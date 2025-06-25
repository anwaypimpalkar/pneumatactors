//
//  MenuView.swift
//  Pneumatactors_App
//
//  Created by Anway Pimpalkar on 6/4/25.
//

import SwiftUI

struct MenuView: View {
    @State private var trainingComplete: Bool = false
    @StateObject private var trialManager = TrialManager()
    @StateObject private var appSettings = AppSettings()
    @StateObject private var networkSettings = NetworkSettings()

    var body: some View {
        NavigationView {
            VStack(spacing: 30) {
                Text("Pneumatactors Controller")
                    .font(.largeTitle)
                    .fontWeight(.semibold)
                    .multilineTextAlignment(.center)
                    .padding(.top)

                Text("© 2025 Anway Pimpalkar")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                    .padding(.bottom, 100)

                NavigationLink(destination:
                    ConfigureView()
                        .environmentObject(appSettings)
                        .environmentObject(networkSettings)
                ) {
                    MenuButtonLabel(title: "Configure")
                }

                NavigationLink(destination: TestView()) {
                    MenuButtonLabel(title: "Test")
                }

                NavigationLink(
                    destination: trainingComplete ?
                        AnyView(DiscriminationPhaseView()
                            .environmentObject(trialManager)
                            .environmentObject(appSettings)
                        ) :
                        AnyView(TrainingPhaseView(trainingComplete: $trainingComplete)
                            .environmentObject(trialManager)
                            .environmentObject(appSettings)
                        )
                ) {
                    MenuButtonLabel(title: "5 × 4 Identification Task")
                }

                Spacer()
            }
            .padding()
            .onAppear {
                let user = appSettings.selectedTrialFile
                    .replacingOccurrences(of: "_trials.json", with: "")
                    .replacingOccurrences(of: ".json", with: "")
                trainingComplete = UserDefaults.standard.bool(forKey: "\(user)_trainingComplete")
            }
        }
    }
}


class NetworkSettings: ObservableObject {
    @Published var ipAddress: String {
        didSet {
            UserDefaults.standard.set(ipAddress, forKey: "ipAddress")
        }
    }

    @Published var port: String {
        didSet {
            UserDefaults.standard.set(port, forKey: "port")
        }
    }

    init() {
        self.ipAddress = UserDefaults.standard.string(forKey: "ipAddress") ?? "192.168.4.1"
        self.port = UserDefaults.standard.string(forKey: "port") ?? "4210"
    }
}


struct MenuButtonLabel: View {
    let title: String

    var body: some View {
        Text(title)
            .frame(maxWidth: .infinity)
            .padding()
            .background(Color.blue)
            .foregroundColor(.white)
            .cornerRadius(12)
            .font(.headline)
    }
}

