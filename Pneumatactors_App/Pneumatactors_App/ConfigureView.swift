////
////  ConfigureView.swift
////  Pneumatactors_App
////
////  Created by Anway Pimpalkar on 6/8/25.
////
//
//
//import SwiftUI
//
//struct ConfigureView: View {
//    @EnvironmentObject var appsettings: AppSettings
//    @EnvironmentObject var settings: NetworkSettings
//    @State private var savedMessage = ""
//
//    @State private var availableFiles: [String] = []
//
//    var body: some View {
//        Form {
//            Section(header: Text("Select User")) {
//                Picker("Trial File", selection: $appsettings.selectedTrialFile) {
//                    ForEach(availableFiles, id: \.self) { file in
//                        Text(file).tag(file)
//                    }
//                }
//            }
//
//            Section(header: Text("UDP Configuration")) {
//                HStack {
//                    Text("IP:")
//                        .frame(width: 60, alignment: .leading)
//                    TextField("e.g. 192.168.0.72", text: $settings.ipAddress)
//                        .keyboardType(.decimalPad)
//                        .textFieldStyle(RoundedBorderTextFieldStyle())
//                }
//
//                HStack {
//                    Text("Port:")
//                        .frame(width: 60, alignment: .leading)
//                    TextField("e.g. 4210", text: $settings.port)
//                        .keyboardType(.numberPad)
//                        .textFieldStyle(RoundedBorderTextFieldStyle())
//                }
//            }
//
//            Button(action: {
//                savedMessage = "Settings saved."
//                DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
//                    savedMessage = ""
//                }
//            }) {
//                Text("Save")
//                    .frame(maxWidth: .infinity)
//                    .padding()
//                    .background(Color.blue)
//                    .foregroundColor(.white)
//                    .cornerRadius(8)
//            }
//
//            if !savedMessage.isEmpty {
//                Text(savedMessage)
//                    .foregroundColor(.gray)
//            }
//        }
//        .navigationTitle("Configure")
//        .onAppear {
//            if let urls = Bundle.main.urls(forResourcesWithExtension: "json", subdirectory: nil) {
//                availableFiles = urls.map { $0.lastPathComponent }.sorted()
//            }
//        }
//    }
//}


import SwiftUI

struct ConfigureView: View {
    @EnvironmentObject var appsettings: AppSettings
    @EnvironmentObject var settings: NetworkSettings
    struct UserProgress: Identifiable {
        let id = UUID()
        let user: String
        let trial: Int
        let trainingComplete: Bool
    }

    @State private var storedProgress: [UserProgress] = []
    @State private var savedMessage = ""
    @State private var availableFiles: [String] = []
    

    var body: some View {
        Form {
            Section(header: Text("Select User")) {
                Picker("Trial File", selection: $appsettings.selectedTrialFile) {
                    ForEach(availableFiles, id: \.self) { file in
                        Text(file).tag(file)
                    }
                }
            }

            Section(header: Text("UDP Configuration")) {
                HStack {
                    Text("IP:")
                        .frame(width: 60, alignment: .leading)
                    TextField("e.g. 192.168.0.72", text: $settings.ipAddress)
                        .keyboardType(.decimalPad)
                        .textFieldStyle(RoundedBorderTextFieldStyle())
                }

                HStack {
                    Text("Port:")
                        .frame(width: 60, alignment: .leading)
                    TextField("e.g. 4210", text: $settings.port)
                        .keyboardType(.numberPad)
                        .textFieldStyle(RoundedBorderTextFieldStyle())
                }
            }

            Section(header: Text("Saved Progress")) {
                ForEach(storedProgress, id: \.user) { progress in
                    HStack {
                        Text("\(progress.user): [T\(progress.trainingComplete ? "✓" : "✗")] Trial \(progress.trial)")
                            .font(.subheadline)
                        Spacer()
                        Button("Reset") {
                            UserDefaults.standard.removeObject(forKey: "\(progress.user)_lastCompletedTrial")
                            UserDefaults.standard.removeObject(forKey: "\(progress.user)_trainingComplete")
                            loadStoredProgress()
                        }
                        .foregroundColor(.red)
                    }
                }
                
                if !storedProgress.isEmpty {
                    Button("Reset All") {
                        for progress in storedProgress {
                            UserDefaults.standard.removeObject(forKey: "\(progress.user)_lastCompletedTrial")
                            UserDefaults.standard.removeObject(forKey: "\(progress.user)_trainingComplete")
                        }
                        loadStoredProgress()
                    }
                    .foregroundColor(.red)
                } else {
                    Text("No saved progress.")
                        .foregroundColor(.gray)
                }
            }

            Button(action: {
                savedMessage = "Settings saved."
                DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                    savedMessage = ""
                }
            }) {
                Text("Save")
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.blue)
                    .foregroundColor(.white)
                    .cornerRadius(8)
            }

            if !savedMessage.isEmpty {
                Text(savedMessage)
                    .foregroundColor(.gray)
            }
        }
        .navigationTitle("Configure")
        .onAppear {
            if let urls = Bundle.main.urls(forResourcesWithExtension: "json", subdirectory: nil) {
                availableFiles = urls.map { $0.lastPathComponent }.sorted()
            }
            loadStoredProgress()
        }
    }

    func loadStoredProgress() {
        var progressList: [UserProgress] = []
        let defaults = UserDefaults.standard

        for (key, value) in defaults.dictionaryRepresentation() {
            if key.hasSuffix("_lastCompletedTrial"),
               let trialIndex = value as? Int {
                let user = key.replacingOccurrences(of: "_lastCompletedTrial", with: "")
                let trainingDone = defaults.bool(forKey: "\(user)_trainingComplete")
                progressList.append(UserProgress(user: user, trial: trialIndex, trainingComplete: trainingDone))
            }
        }

        storedProgress = progressList.sorted(by: { $0.user < $1.user })
    }
}
