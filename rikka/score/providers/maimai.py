from dataclasses import dataclass
from typing import TypeAlias, cast

from httpx import HTTPStatusError
from maimai_py import (
    DivingFishPlayer,
    DivingFishProvider,
    FCType,
    LXNSPlayer,
    LXNSProvider,
    MaimaiClient,
    MaimaiScores,
    Player,
    PlayerIdentifier,
    ScoreExtend,
)
from nonebot import logger
from nonebot_plugin_alconna import At, UniMessage
from nonebot_plugin_orm import async_scoped_session

from ...config import config
from ...database import UserBindInfo, UserBindInfoORM
from .._base import BaseScoreProvider
from .._schema import (
    PlayerMaiB50,
    PlayerMaiInfo,
    PlayerMaiScore,
    ScoreFCType,
    ScoreFSType,
    ScoreRateType,
    SongDifficulty,
    SongType,
)

_SUPPORT_PROVIDER: TypeAlias = DivingFishProvider | LXNSProvider

maimai_client = MaimaiClient()
_divingfish_provider = DivingFishProvider(developer_token=config.divingfish_developer_api_key)
_lxns_provider = LXNSProvider(developer_token=config.lxns_developer_api_key)


@dataclass
class MaimaiPyParams:
    score_provider: _SUPPORT_PROVIDER
    identifier: PlayerIdentifier


class MaimaiPyScoreProvider(BaseScoreProvider[MaimaiPyParams]):
    provider = "maimai_py"
    ParamsType = MaimaiPyParams

    @staticmethod
    def _score_unpack(score: ScoreExtend) -> PlayerMaiScore:
        return PlayerMaiScore(
            song_id=score.id,
            song_name=score.title,
            song_type=SongType(score.type.value),
            song_level=score.level,
            song_difficulty=SongDifficulty(score.level_index.value),
            achievements=score.achievements,  # type:ignore
            dx_score=score.dx_score or 0,
            dx_star=0,  # unsupported.
            dx_rating=score.dx_rating or 0,
            rate=ScoreRateType(score.rate.name.lower()),
            fc=ScoreFCType(score.fc.name.lower()) if score.fc else None,
            fs=ScoreFSType(score.fs.name.lower()) if score.fs else None,
        )

    @staticmethod
    def _unpack_player_mai_info(player: Player | LXNSPlayer | DivingFishPlayer) -> "PlayerMaiInfo":
        if isinstance(player, LXNSPlayer):
            player_info = PlayerMaiInfo(
                name=player.name,
                rating=player.rating,
                course_rank=player.course_rank,
                class_rank=player.class_rank,
                friend_code=str(player.friend_code),
                trophy=player.trophy,
                icon=player.icon,
                name_plate=player.name_plate,
                frame=player.frame,
                upload_time=player.upload_time,
            )
        else:
            player_info = PlayerMaiInfo(
                name=player.name,
                rating=player.rating,
            )

        return player_info

    @staticmethod
    async def auto_get_score_provider(session: async_scoped_session, user_id: str) -> _SUPPORT_PROVIDER:
        """
        根据用户绑定情况自动获取合适的查分器
        """
        bind_info = await UserBindInfoORM.get_user_bind_info(session, user_id)

        if bind_info and not bind_info.lxns_api_key and bind_info.diving_fish_import_token:
            return _divingfish_provider

        return _lxns_provider

    @staticmethod
    async def auto_get_player_identifier(
        session: async_scoped_session, user_id: str, score_provider: _SUPPORT_PROVIDER
    ) -> PlayerIdentifier:
        """
        根据用户绑定情况自动选择鉴权方式
        """
        logger.debug(f"[{user_id}] 1/4 尝试从数据库中获取玩家绑定信息...")
        user_bind_info = await UserBindInfoORM.get_user_bind_info(session, user_id)

        # 落雪查分器
        if isinstance(score_provider, LXNSProvider):
            new_player_friend_code = None
            # When user_bind_info is None, score_provider is LXNSScoreProvider.
            if user_bind_info is None:
                logger.warning(f"[{user_id}] 未能获取玩家码，数据库中不存在绑定的玩家数据")
                logger.debug(f"[{user_id}] 1/4 尝试通过 QQ 请求玩家数据")
                try:
                    identifier = PlayerIdentifier(qq=int(user_id))
                    player_obj = await score_provider.get_player(identifier, client=maimai_client)
                    new_player_friend_code = player_obj.friend_code
                except HTTPStatusError as e:
                    logger.warning(
                        f"[{user_id}] 无法通过 QQ 号请求玩家数据: {e.response.status_code}: {e.response.text}"
                    )

                    await UniMessage(
                        [
                            At(flag="user", target=user_id),
                            "你还未绑定查分器，请使用 /bind 指令进行绑定！",
                        ]
                    ).finish()

                    return

            friend_code = new_player_friend_code or user_bind_info.friend_code  # type:ignore
            if not friend_code:
                logger.warning(f"[{user_id}] 无法获取好友码，无法继续查询。")
                await UniMessage(
                    [
                        At(flag="user", target=user_id),
                        "无法获取好友码，请确认已绑定或查分器可用。",
                    ]
                ).finish()
                return

            identifier = PlayerIdentifier(friend_code=int(friend_code))

        # 水鱼查分器
        # elif isinstance(score_provider, DivingFishScoreProvider):
        else:
            # When score_provider is DivingFish, user_bind_info and diving_fish_username is not None.
            user_bind_info = cast(UserBindInfo, user_bind_info)
            diving_fish_username = user_bind_info.diving_fish_username
            assert diving_fish_username
            identifier = PlayerIdentifier(username=diving_fish_username)

        return identifier

    async def fetch_player_info(self, params: MaimaiPyParams) -> PlayerMaiInfo:
        player_info = await maimai_client.players(params.identifier, params.score_provider)

        return self._unpack_player_mai_info(player_info)

    async def fetch_player_b50(self, params: MaimaiPyParams) -> PlayerMaiB50:
        player_b50 = await maimai_client.bests(params.identifier, params.score_provider)

        best35 = [self._score_unpack(score) for score in player_b50.scores_b35]
        best15 = [self._score_unpack(score) for score in player_b50.scores_b15]

        return PlayerMaiB50(best35, best15)

    async def fetch_player_ap50(self, params: MaimaiPyParams) -> PlayerMaiB50:
        """
        获得玩家 AP 50

        注: 落雪查分器需要使用个人 token 进行鉴权
        """
        logger.debug("1/2 获取完整游玩记录")

        scores = await maimai_client.scores(params.identifier, params.score_provider)

        ap_records = scores.filter(fc=FCType.AP) + scores.filter(fc=FCType.APP)

        logger.debug("2/2 划分版本信息")

        ap50 = await MaimaiScores(maimai_client).configure(ap_records, b50_only=True)

        best35 = [self._score_unpack(score) for score in ap50.scores_b35]
        best15 = [self._score_unpack(score) for score in ap50.scores_b15]

        return PlayerMaiB50(best35, best15)
