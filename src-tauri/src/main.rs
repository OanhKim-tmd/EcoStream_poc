// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    tauri::Builder::default()
        .setup(|_app| {
            println!("EcoStream Desktop Native Window initialized.");
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running EcoStream application");
}
