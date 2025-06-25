//
//  GridButtonView.swift
//  Pneumatactors_App
//
//  Created by Anway Pimpalkar on 6/5/25.
//

import SwiftUI


struct GridButtonView: View {
    let pumpLevel: Int
    let valveLevel: Int
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            VStack(spacing: 0) {
                ZStack {
                    Color.blue.brightness(brightnessForPump(pumpLevel))
                    Text("P = \(pumpLevel)")
                        .foregroundColor(.white)
                        .font(.subheadline)
                        .bold()
                }
                .frame(height: 50)

                ZStack {
                    Color.red.brightness(brightnessForValve(valveLevel))
                    Text("V = \(valveLevel)")
                        .foregroundColor(.white)
                        .font(.subheadline)
                        .bold()
                }
                .frame(height: 50)
            }
            .frame(width: 100, height: 100)
            .cornerRadius(5)
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .stroke(isSelected ? Color.green : Color.white.opacity(0.2), lineWidth: isSelected ? 3 : 1)
            )
        }
    }

    private func brightnessForPump(_ level: Int) -> Double {
        switch level {
        case 1: return 0.3
        case 2: return 0.0
        case 3: return -0.3
        default: return 0
        }
    }

    private func brightnessForValve(_ level: Int) -> Double {
        switch level {
        case 1: return 0.3
        case 2: return 0.0
        case 3: return -0.3
        default: return 0
        }
    }
}
