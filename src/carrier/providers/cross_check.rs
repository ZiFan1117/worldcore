use super::Registry;

/// ★ **执行清单声明的能力 ↔ 执行器自报的能力：对账**（2026-10-04 立）。
///
/// ## 它补的是哪一格（**"从来没人读过的那一格"**）
///
/// [`Provider::capabilities`] 自契约建立起就在，但**在 `src/**` 里零调用点**——
/// 当时 `.capabilities()` 的全部命中都是 `policy.capabilities()`（门禁那一份），
/// **不是执行器这一份**。后果是：清单说"这项能力交给 `backlight` 干"，
/// 而 `backlight` 自己说"我能干的是另一件事"，**两句话可以永远并存，没有任何东西会因此变红**。
///
/// ## 判据（**会红**）
///
/// `cap.d` 里 `provider = P` 的那一项，其 `capability`（**语义层的名字**）必须出现在
/// `P.capabilities()` 里。两边**各有一个合法名字、却不是同一个** ⇒ 红。
///
/// ★ **反例的形态是"两套词表撞车"，不是拼写错**：`notice.mute` 在本体 `_interfaces` 里合法，
/// `brightness.set` 在背光执行器那套词表里**也合法**——可它们不是同一个名字。
/// 拼写错（`brightnes.set`）谁都看得出来；**两套各自合法的词表撞车，只有把这一格接上才看得见**。
///
/// ## 边界（**两条判据不互相冒充**）
///
/// 执行器**根本没注册**不属本条：那是 [`execute`] 第 3 步的"没有对应的执行器"，
/// 本条对它**跳过、不报**——否则同一件事会有两个说法。
///
/// ## 返回
///
/// 全部不一致（**不是第一处**）：有几项就报几项，一项一个字符串，便于一次改完。
pub fn cross_check(
    manifest: &crate::carrier::capd::Manifest,
    registry: &Registry,
) -> Result<(), Vec<String>> {
    let mut bad = Vec::new();
    for cap in manifest.iter() {
        let Some(p) = registry.get(&cap.provider) else {
            // 没注册 ⇒ 第 3 步正面回答它，本条不冒充那条判据。
            continue;
        };
        if !p.capabilities().iter().any(|c| *c == cap.name) {
            bad.push(format!(
                "`{}`：清单把它交给执行器 `{}`，而 `{}` 自报的能力是 {:?} \
                 —— 两边各有一个合法名字，却不是同一个（不是拼写错）",
                cap.name,
                cap.provider,
                cap.provider,
                p.capabilities()
            ));
        }
    }
    if bad.is_empty() {
        Ok(())
    } else {
        Err(bad)
    }
}
