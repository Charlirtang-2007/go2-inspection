use mdns_sd::{ServiceDaemon, ServiceEvent};
use std::time::Duration;
use tokio::time::timeout;

// ============================================================
// mDNS 后端发现
// ============================================================

/// 通过 mDNS 发现 Go2 后端
/// 返回格式: "http://192.168.143.206:8000"
#[tauri::command]
async fn discover_backend() -> Result<String, String> {
    println!("🔍 [Rust] 开始搜索 Go2 后端...");

    let mdns = ServiceDaemon::new().map_err(|e| format!("创建 mDNS 失败: {}", e))?;

    let receiver = mdns
        .browse("_go2-backend._tcp.local.")
        .map_err(|e| format!("浏览服务失败: {}", e))?;

    // 5 秒超时
    let result = timeout(Duration::from_secs(5), async {
        loop {
            match receiver.recv_async().await {
                Ok(ServiceEvent::ServiceResolved(info)) => {
                    let port = info.get_port();
                    if let Some(ip) = info.get_addresses().iter().next() {
                        let url = format!("http://{}:{}", ip, port);
                        println!("✅ [Rust] 发现后端: {}", url);
                        return Ok::<String, String>(url);
                    }
                }
                Ok(_) => continue,
                Err(e) => return Err(format!("接收事件失败: {}", e)),
            }
        }
    })
    .await;

    let _ = mdns.shutdown();

    match result {
        Ok(Ok(url)) => Ok(url),
        Ok(Err(e)) => Err(e),
        Err(_) => Err("发现超时：未找到 Go2 后端服务".to_string()),
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