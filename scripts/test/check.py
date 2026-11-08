#!/usr/bin/env python3
"""我方判据入口（13-aios-worldcore）。

★ 本目录 verify/ 是**我方新增**（非上游；上游的检查在 distro/build/tests/ 与 .gitlab-ci.yml）。
跑法：
  python verify/check.py            跑全部判据
  python verify/check.py --self-test 只跑各判据的反例自检
退出码：0 全绿 ／ 1 有红 ／ 2 有环境问题（★ 未校验 ≠ 通过）
"""
import os
import subprocess
import sys

# ★ 输出与子进程都强制 UTF-8：本机默认 GBK，否则入口自己印中文就崩（2026-10-13 实测）
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

CHILD_ENV = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")

HERE = os.path.dirname(os.path.abspath(__file__))
CRITERIA = [
    "c1_upstream_parity.py",
    "c2_domain_files_only.py",
    "c3_action_name_gate.py",
    "c4_eol_consistency.py",
    "c5_policy_kernel_attached.py",
    "c6_class_has_identity.py",
    "c7_reference_integrity.py",
    "c8_role_has_ceiling.py",
    "c9_silent_fallbacks_registered.py",
    "c10_removal_carries_reason.py",
    "c11_recovery_depends_on_l1l2_only.py",
    "c12_ontology_text_has_no_bad_escapes.py",
    "c13_one_vocabulary.py",
    "c14_no_command_literal.py",
    "c15_registration_and_transport.py",
    "c16_registration_kind.py",
    "c17_authorization.py",
    "c18_ledger_persisted.py",
    "c19_outbound_port.py",
    "c20_identity_source.py",
    "c21_permit.py",
    "c22_command_bridge.py",
    "c23_commands_run.py",
    "c24_a2ui_projection.py",
    "c25_bus_and_ontology_units.py",
    "c26_only_zenoh_no_data_plane.py",
    "c27_file_length.py",
    "c28_py_layout.py",
    "c29_reject_codes.py",
    "c30_state_ownership.py",
    "c31_history_query.py",
    "c32_action_contract.py",
    "c33_manual_generated.py",
    "c34_owl_export.py",
    "c35_law_declared.py",
    "c36_action_semantics.py",
    "c37_interfaces.py",
    "c38_desktop_windows.py",
    "c39_ontology_window.py",
    "c40_agent_screen.py",
    "c41_ledger_privacy.py",
    "c42_state_actions.py",
    "c43_dsh_bridge.py",
    "c44_monitor_goal.py",
    "c45_event_stream.py",
    "c46_event_replay.py",
    "c47_world_snapshot.py",
    "c48_round_eval.py",
    "c49_worldfs.py",
    "c50_guard_process.py",
    "c51_guard_exec.py",
    "c52_web_voice.py",
    "c53_a2ui_conformance.py",
    "c54_agent_heartbeat.py",
    "c55_scene_files.py",
    "c56_law_proposal.py",
    "c57_status.py",
    "c58_final_report.py",
    "c59_governance.py",
    "c60_semantic_browser.py",
    "c61_guard_popup.py",
    "c62_desktop_confirm.py",
    "c63_desktop_browser_icon.py",
    "c64_semantic_browse.py",
    "c65_computer_live.py",
    "c66_change_driven.py",
    "c67_ingest_pipeline.py",
    "c68_pipeline_deep.py",
    "c69_fs_process.py",
    "c70_clock_process.py",
    "c71_recovery_process.py",
    "c72_network_process.py",
    "c73_agent_exec_reply.py",
    "c74_agent_action_memory.py",
    "c75_vault_process.py",
    "c76_worldfs.py",
    "c77_functions.py",
    "c78_builtin_actions.py",
    "c79_worldfs_fuse.py",
    "c85_worldfs_no_local_ledger.py",
    "c86_provider_auth.py",
    "c87_bus_acl.py",
    "c88_topic_acl.py",
    "c89_network_deep.py",
    "c90_clock_time.py",
    "c91_worldfs_semantic.py",
    "c92_snapshot_worldfs.py",
    "c93_dsh_console.py",
    "c94_dsh_web.py",
    "c95_desktop_dsh.py",
    "c96_agent_workspace.py",
    "c97_ticket_persist.py",
    "c98_protocol_five_elements.py",
    "c100_message_protocol.py",
    "c101_external_contributions.py",
    "c102_permit_protocol.py",
    "c103_keys_acl.py",
    "c104_protocol_sdk.py",
    "c105_action_contract.py",
    "c106_law_contract.py",
    "c107_provider_binding.py",
    "c108_registration_law.py",
    "c109_register_envelope.py",
    "c110_provider_auth_p2.py",
    "c111_individual_protocol.py",
    "c112_agent_register.py",
    "c113_provider_register.py",
    "c114_binding_gate.py",
    "c115_p2_call.py",
    "c116_state_rules.py",
    "c117_agent_p2_client.py",
    "c118_registration_idempotent.py",
    "c119_p2_call_negative.py",
    "c120_fs_p2_route.py",
    "c121_p2_provider_install.py",
    "c122_state_report.py",
    "c123_world_gateway.py",
]


def main(argv):
    self_test = "--self-test" in argv
    rows = []
    worst = 0
    for name in CRITERIA:
        path = os.path.join(HERE, name)
        cmd = [sys.executable, path] + (["--self-test"] if self_test else [])
        p = subprocess.run(cmd, capture_output=True, text=True, env=CHILD_ENV,
                           encoding="utf-8", errors="replace")
        out = (p.stdout or "").strip()
        rows.append((name, p.returncode, out))
        if p.returncode == 1:
            worst = 1
        elif p.returncode != 0 and worst == 0:
            worst = 2
    print("=== 13-aios-worldcore · 我方判据（%s）===" % ("反例自检" if self_test else "实跑"))
    for name, rc, out in rows:
        mark = {0: "GREEN", 1: "RED  ", 2: "ENV  "}.get(rc, "?    ")
        print("[%s] %s" % (mark, name))
        for line in out.splitlines():
            print("        " + line)
    _tree = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", shell=False).stdout.splitlines()
    print("    工作树：%d 个未提交改动（★ 判据读的是**工作树**，不是 HEAD）" % len(_tree))

    print("=== 结论：%s（rc=%d）===" % ({0: "全绿", 1: "有红", 2: "有环境问题（未校验）"}.get(worst, "?"), worst))
    return worst


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))