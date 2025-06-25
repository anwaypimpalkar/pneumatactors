//
//  Pneumatactors_AppApp.swift
//  Pneumatactors_App
//
//  Created by Anway Pimpalkar on 6/4/25.
//

import SwiftUI

@main
struct Pneumatactor_App: App {
    @StateObject private var appSettings = AppSettings()
    @StateObject private var networkSettings = NetworkSettings()

    var body: some Scene {
        WindowGroup {
            MenuView()
                .environmentObject(appSettings)
                .environmentObject(networkSettings)
        }
    }
}
