use tauri::{
    menu::{Menu, MenuItem},
    tray::TrayIconBuilder,
    Manager,
};
use tauri_plugin_global_shortcut::{Code, GlobalShortcutExt, Modifiers, Shortcut};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_clipboard_manager::init())
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            // Build tray menu
            let show_i = MenuItem::with_id(app, "show", "Show STRIX", true, None::<&str>)?;
            let quit_i = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show_i, &quit_i])?;

            // Create tray icon
            TrayIconBuilder::new()
                .menu(&menu)
                .tooltip("STRIX - Fact Checker")
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "show" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                    "quit" => {
                        app.exit(0);
                    }
                    _ => {}
                })
                .build(app)?;

            // Register global shortcut: Cmd+Shift+X
            let shortcut = Shortcut::new(
                Some(Modifiers::SUPER | Modifiers::SHIFT),
                Code::KeyX,
            );

            let app_handle = app.handle().clone();
            app.global_shortcut().on_shortcut(shortcut, move |_app, _shortcut, _event| {
                // Read clipboard content (the user has selected + copied text)
                // We emit an event to the frontend which handles the API call
                let handle = app_handle.clone();

                // Use clipboard plugin to read selected text
                // The workflow: user selects text, presses shortcut,
                // we simulate Cmd+C, read clipboard, then send to frontend
                tauri::async_runtime::spawn(async move {
                    // Small delay to ensure clipboard is ready
                    tokio::time::sleep(std::time::Duration::from_millis(100)).await;

                    // Try to get clipboard text
                    if let Some(window) = handle.get_webview_window("main") {
                        let _ = window.show();
                        let _ = window.set_focus();

                        // Read clipboard via the frontend (Tauri plugin)
                        let _ = window.emit("trigger-check", ());
                    }
                });
            })?;

            // Hide window on launch (tray-only)
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.hide();
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running STRIX");
}
