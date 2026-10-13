//! MVP 演示：把一份 AIOS 翻译器的产出喂给本体，看它过不过。
//!
//! 用法：
//!   demo                     打印本体摘要
//!   demo <action_name>       校验一个动作名（参数留空）
//!   demo <action_name> <json>  用给定的参数 JSON 校验

use aios_ontology::Ontology;

const DATA: &str = include_str!("../../data/ontology.json");

fn main() {
    let ontology = Ontology::load_str(DATA).expect("我们的本体应当装载得起来");
    let args: Vec<String> = std::env::args().skip(1).collect();

    if args.is_empty() {
        println!("本体摘要");
        println!("  动作名 {} 条: {}", ontology.action_names().len(), ontology.action_names().join(", "));
        println!("  能力   {} 条: {}", ontology.capability_names().len(), ontology.capability_names().join(", "));
        println!("  入口表 {} 条（现取 0 —— 本体自己登记的缺口）", ontology.function_entry_count());
        println!("  已登记宿主命令 {} 条", ontology.host_command_count());
        for gap in ontology.declared_gaps() {
            println!("  缺口: {gap}");
        }
        return;
    }

    let action_name = &args[0];
    let parameters = if args.len() > 1 { args[1].clone() } else { "{}".to_string() };
    let translated = format!(
        "{{\"action_name\":\"{action_name}\",\"parameters\":{parameters},\"confidence\":1.0,\"reasoning\":\"MVP 演示\"}}"
    );
    println!("喂给本体的翻译器产出: {translated}");
    match ontology.validate_translation(&translated) {
        Ok(v) => {
            println!("  判定: 过");
            println!("  命中能力: {}", v.capability);
            println!("  缺的必填参数: {:?}", v.missing_required_parameters);
        }
        Err(e) => {
            println!("  判定: 拒");
            println!("  错误码: {}", e.code());
            println!("  说明: {e}");
        }
    }
}
