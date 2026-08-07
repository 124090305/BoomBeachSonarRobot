from __future__ import annotations

from dataclasses import dataclass

import config
from controllers.adb_controller import (
    AdbController,
)
from logger import get_logger


logger = get_logger(__name__)


@dataclass(frozen=True)
class NetworkState:
    """当前游戏网络规则状态。"""

    uid: int

    weak_ipv4: bool
    weak_ipv6: bool | None

    reject_ipv4: bool
    reject_ipv6: bool | None

    @property
    def weak_enabled(
        self,
    ) -> bool:
        return (
            self.weak_ipv4
            or self.weak_ipv6 is True
        )

    @property
    def reject_enabled(
        self,
    ) -> bool:
        return (
            self.reject_ipv4
            or self.reject_ipv6 is True
        )

    def to_text(
        self,
    ) -> str:
        def mark(
            value: bool | None,
        ) -> str:
            if value is None:
                return "不可用"

            return (
                "开启"
                if value
                else "关闭"
            )

        return (
            f"游戏 UID：{self.uid}\n"
            f"弱网 IPv4：{mark(self.weak_ipv4)}\n"
            f"弱网 IPv6：{mark(self.weak_ipv6)}\n"
            f"断网 IPv4：{mark(self.reject_ipv4)}\n"
            f"断网 IPv6：{mark(self.reject_ipv6)}"
        )


class NetworkController:
    """只控制指定游戏 UID 的网络。"""

    def __init__(
        self,
        adb: AdbController,
        package_name: str = config.GAME_PACKAGE_NAME,
    ) -> None:
        self.adb = adb

        self.package_name = (
            package_name.strip()
        )

        if not self.package_name:
            raise ValueError(
                "游戏包名不能为空"
            )

        self._ip6tables_available: (
            bool | None
        ) = None

    # =========================================================
    # 基础检查
    # =========================================================

    def ensure_ready(
        self,
    ) -> tuple[str, int]:
        """
        检查：
        设备
        游戏
        ROOT
        iptables
        UID
        """
        logger.debug(
            "检查网络控制环境"
        )

        self.adb.ensure_device_online()

        installed = (
            self.adb.is_package_installed(
                self.package_name
            )
        )

        if not installed:
            raise RuntimeError(
                "设备中没有找到游戏包 "
                f"{self.package_name}"
            )

        root_mode = (
            self.adb.ensure_root_shell()
        )

        result = (
            self.adb.run_privileged(
                (
                    "command -v iptables "
                    ">/dev/null 2>&1"
                ),
                check=False,
            )
        )

        if result.returncode != 0:
            raise RuntimeError(
                "当前模拟器没有可用 iptables，"
                "无法控制游戏网络"
            )

        uid = self.adb.get_package_uid(
            self.package_name
        )

        logger.debug(
            "网络控制环境正常：ROOT=%s，UID=%s",
            root_mode,
            uid,
        )

        return root_mode, uid

    def get_root_info(
        self,
    ) -> str:
        """返回 ROOT 模式与 UID。"""
        root_mode, uid = (
            self.ensure_ready()
        )

        return (
            f"ROOT 模式：{root_mode}\n"
            f"游戏 UID：{uid}"
        )

    # =========================================================
    # DROP 弱网
    # =========================================================

    def enable_weak_network(
        self,
    ) -> None:
        """开启 DROP 弱网。"""
        logger.info(
            "正在开启弱网 DROP"
        )

        _root_mode, uid = (
            self.ensure_ready()
        )

        self._apply_rule(
            command="iptables",
            chain=config.WEAK_NETWORK_CHAIN,
            uid=uid,
            mode="drop",
            enabled=True,
        )

        if self._has_ip6tables():
            self._apply_rule(
                command="ip6tables",
                chain=config.WEAK_NETWORK_CHAIN,
                uid=uid,
                mode="drop",
                enabled=True,
                check=False,
            )

        self.adb.delay(
            config.NETWORK_APPLY_DELAY
        )

        logger.info(
            "弱网 DROP 已开启：UID=%s",
            uid,
        )

    def disable_weak_network(
        self,
    ) -> None:
        """关闭 DROP 弱网。"""
        logger.info(
            "正在关闭弱网 DROP"
        )

        _root_mode, uid = (
            self.ensure_ready()
        )

        self._apply_rule(
            command="iptables",
            chain=config.WEAK_NETWORK_CHAIN,
            uid=uid,
            mode="drop",
            enabled=False,
        )

        if self._has_ip6tables():
            self._apply_rule(
                command="ip6tables",
                chain=config.WEAK_NETWORK_CHAIN,
                uid=uid,
                mode="drop",
                enabled=False,
                check=False,
            )

        self.adb.delay(
            config.NETWORK_APPLY_DELAY
        )

        logger.info(
            "弱网 DROP 已关闭：UID=%s",
            uid,
        )

    # =========================================================
    # REJECT 断网
    # =========================================================

    def enable_reject_network(
        self,
    ) -> None:
        """开启 REJECT 断网。"""
        logger.info(
            "正在开启断网 REJECT"
        )

        _root_mode, uid = (
            self.ensure_ready()
        )

        self._apply_rule(
            command="iptables",
            chain=config.REJECT_NETWORK_CHAIN,
            uid=uid,
            mode="reject",
            enabled=True,
        )

        if self._has_ip6tables():
            self._apply_rule(
                command="ip6tables",
                chain=config.REJECT_NETWORK_CHAIN,
                uid=uid,
                mode="reject",
                enabled=True,
                check=False,
            )

        self.adb.delay(
            config.NETWORK_APPLY_DELAY
        )

        logger.info(
            "断网 REJECT 已开启：UID=%s",
            uid,
        )

    def disable_reject_network(
        self,
    ) -> None:
        """关闭 REJECT 断网。"""
        logger.info(
            "正在关闭断网 REJECT"
        )

        _root_mode, uid = (
            self.ensure_ready()
        )

        self._apply_rule(
            command="iptables",
            chain=config.REJECT_NETWORK_CHAIN,
            uid=uid,
            mode="reject",
            enabled=False,
        )

        if self._has_ip6tables():
            self._apply_rule(
                command="ip6tables",
                chain=config.REJECT_NETWORK_CHAIN,
                uid=uid,
                mode="reject",
                enabled=False,
                check=False,
            )

        self.adb.delay(
            config.NETWORK_APPLY_DELAY
        )

        logger.info(
            "断网 REJECT 已关闭：UID=%s",
            uid,
        )

    # =========================================================
    # 恢复与状态
    # =========================================================

    def restore_network(
        self,
    ) -> None:
        """清理 DROP 与 REJECT。"""
        logger.info(
            "正在恢复游戏网络"
        )

        _root_mode, uid = (
            self.ensure_ready()
        )

        for command in (
            self._available_table_commands()
        ):
            self._apply_rule(
                command=command,
                chain=config.WEAK_NETWORK_CHAIN,
                uid=uid,
                mode="drop",
                enabled=False,
                check=False,
            )

            self._apply_rule(
                command=command,
                chain=config.REJECT_NETWORK_CHAIN,
                uid=uid,
                mode="reject",
                enabled=False,
                check=False,
            )

        self.adb.delay(
            config.NETWORK_APPLY_DELAY
        )

        logger.info(
            "游戏网络已恢复：UID=%s",
            uid,
        )

    def get_state(
        self,
    ) -> NetworkState:
        """读取当前真实网络规则。"""
        _root_mode, uid = (
            self.ensure_ready()
        )

        weak_ipv4 = (
            self._rule_exists(
                "iptables",
                config.WEAK_NETWORK_CHAIN,
                uid,
            )
        )

        reject_ipv4 = (
            self._rule_exists(
                "iptables",
                config.REJECT_NETWORK_CHAIN,
                uid,
            )
        )

        if self._has_ip6tables():
            weak_ipv6: (
                bool | None
            ) = self._rule_exists(
                "ip6tables",
                config.WEAK_NETWORK_CHAIN,
                uid,
            )

            reject_ipv6: (
                bool | None
            ) = self._rule_exists(
                "ip6tables",
                config.REJECT_NETWORK_CHAIN,
                uid,
            )

        else:
            weak_ipv6 = None
            reject_ipv6 = None

        state = NetworkState(
            uid=uid,
            weak_ipv4=weak_ipv4,
            weak_ipv6=weak_ipv6,
            reject_ipv4=reject_ipv4,
            reject_ipv6=reject_ipv6,
        )

        logger.debug(
            "网络状态：弱网=%s，断网=%s",
            state.weak_enabled,
            state.reject_enabled,
        )

        return state

    # =========================================================
    # 内部方法
    # =========================================================

    def _available_table_commands(
        self,
    ) -> list[str]:
        commands = [
            "iptables"
        ]

        if self._has_ip6tables():
            commands.append(
                "ip6tables"
            )

        return commands

    def _has_ip6tables(
        self,
    ) -> bool:
        if (
            self._ip6tables_available
            is not None
        ):
            return (
                self._ip6tables_available
            )

        result = (
            self.adb.run_privileged(
                (
                    "command -v ip6tables "
                    ">/dev/null 2>&1"
                ),
                check=False,
            )
        )

        self._ip6tables_available = (
            result.returncode == 0
        )

        logger.debug(
            "ip6tables 可用：%s",
            self._ip6tables_available,
        )

        return (
            self._ip6tables_available
        )

    def _rule_exists(
        self,
        command: str,
        chain: str,
        uid: int,
    ) -> bool:
        script = (
            f"{command} -C OUTPUT "
            f"-m owner --uid-owner {uid} "
            f"-j {chain}"
        )

        result = (
            self.adb.run_privileged(
                script,
                check=False,
            )
        )

        return (
            result.returncode == 0
        )

    def _apply_rule(
        self,
        *,
        command: str,
        chain: str,
        uid: int,
        mode: str,
        enabled: bool,
        check: bool = True,
    ) -> None:
        if mode == "drop":
            script = (
                self._build_drop_script(
                    command,
                    chain,
                    uid,
                    enabled,
                )
            )

        elif mode == "reject":
            script = (
                self._build_reject_script(
                    command,
                    chain,
                    uid,
                    enabled,
                )
            )

        else:
            raise ValueError(
                "未知网络规则类型："
                f"{mode}"
            )

        logger.debug(
            "应用网络规则：command=%s，chain=%s，uid=%s，mode=%s，enabled=%s",
            command,
            chain,
            uid,
            mode,
            enabled,
        )

        self.adb.run_privileged(
            script,
            check=check,
        )

    @staticmethod
    def _build_drop_script(
        command: str,
        chain: str,
        uid: int,
        enabled: bool,
    ) -> str:
        if enabled:
            return (
                f"{command} -N {chain} "
                f"2>/dev/null || true; "

                f"{command} -C {chain} "
                f"-j DROP 2>/dev/null "
                f"|| {command} -A {chain} "
                f"-j DROP; "

                f"{command} -C OUTPUT "
                f"-m owner --uid-owner {uid} "
                f"-j {chain} 2>/dev/null "
                f"|| {command} -I OUTPUT "
                f"-m owner --uid-owner {uid} "
                f"-j {chain}"
            )

        return (
            f"while {command} -C OUTPUT "
            f"-m owner --uid-owner {uid} "
            f"-j {chain} 2>/dev/null; "

            f"do {command} -D OUTPUT "
            f"-m owner --uid-owner {uid} "
            f"-j {chain}; done; "

            f"{command} -F {chain} "
            f"2>/dev/null || true; "

            f"{command} -X {chain} "
            f"2>/dev/null || true"
        )

    @staticmethod
    def _build_reject_script(
        command: str,
        chain: str,
        uid: int,
        enabled: bool,
    ) -> str:
        if enabled:
            unreachable = (
                "icmp6-port-unreachable"
                if command == "ip6tables"
                else "icmp-port-unreachable"
            )

            return (
                f"{command} -N {chain} "
                f"2>/dev/null || true; "

                f"{command} -F {chain}; "

                f"{command} -A {chain} "
                f"-p tcp "
                f"-j REJECT "
                f"--reject-with tcp-reset; "

                f"{command} -A {chain} "
                f"-j REJECT "
                f"--reject-with {unreachable}; "

                f"{command} -C OUTPUT "
                f"-m owner --uid-owner {uid} "
                f"-j {chain} 2>/dev/null "
                f"|| {command} -I OUTPUT "
                f"-m owner --uid-owner {uid} "
                f"-j {chain}"
            )

        return (
            f"while {command} -C OUTPUT "
            f"-m owner --uid-owner {uid} "
            f"-j {chain} 2>/dev/null; "

            f"do {command} -D OUTPUT "
            f"-m owner --uid-owner {uid} "
            f"-j {chain}; done; "

            f"{command} -F {chain} "
            f"2>/dev/null || true; "

            f"{command} -X {chain} "
            f"2>/dev/null || true"
        )
