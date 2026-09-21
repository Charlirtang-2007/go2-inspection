use mdns_sd::{ServiceDaemon, ServiceEvent};
use std::time::Duration;

// ============================================================
// mDNS 后端发现（每 3 秒轮询直到发现）
// ============================================================

/// 通过 mDNS 发现 Go2 后端
/// 返回格式: "http://192.168.143.206:8000"
/// 每 3 秒打印一次进度，直到发现服务为止
#[tauri::command]
async fn discover_backend() -> Result<String, String> {
    println!("🔍 [Rust] 开始搜索 Go2 后端（每 3 秒轮询）...");

    let mdns = ServiceDaemon::new().map_err(|e| format!("创建 mDNS 失败: {}", e))?;

    let receiver = mdns
        .browse("_go2-backend._tcp.local.")
        .map_err(|e| format!("浏览服务失败: {}", e))?;

    let tick = Duration::from_secs(3);
    let mut elapsed: u64 = 0;

    loop {
        // 每轮等待 3 秒，看是否有事件
        let event = tokio::time::timeout(tick, receiver.recv_async()).await;

        match event {
            Ok(Ok(ServiceEvent::ServiceResolved(info))) => {
                let port = info.get_port();
                if let Some(ip) = info.get_addresses().iter().next() {
                    let url = format!("http://{}:{}", ip, port);
                    println!("✅ [Rust] 发现后端: {}", url);
                    let _ = mdns.shutdown();
                    return Ok(url);
                }
            }
            Ok(Ok(_)) => {
                // 其他事件（ServiceFound / ServiceRemoved 等），忽略
                continue;
            }
            Ok(Err(e)) => {
                println!("⚠️ [Rust] 接收事件失败: {}，继续等待", e);
            }
            Err(_) => {
                // 本轮超时，打印进度
                elapsed += 3;
                println!("🔍 [Rust] 已等待 {} 秒，继续搜索...", elapsed);
            }
        }
    }
}

// ============================================================
// Tauri 入口
// ============================================================

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![discover_backend])
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}