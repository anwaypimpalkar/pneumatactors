//
//  AppSettings.swift
//  Pneumatactors_App
//
//  Created by Anway Pimpalkar on 6/8/25.
//


import Foundation

class AppSettings: ObservableObject {
    @Published var selectedTrialFile: String = "demo.json" // default
}
