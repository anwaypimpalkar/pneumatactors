//
//  Trial.swift
//  Pneumatactors_App
//
//  Created by Anway Pimpalkar on 6/5/25.
//


import Foundation

struct Trial: Codable, Identifiable {
    let id = UUID()
    let valve1: Int
    let valve2: Int
    let pump1: Int
    let pump2: Int
    let label: String // e.g., "P1-V2"
}
