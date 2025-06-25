////
////  DiscriminationPhaseView.swift
////  Pneumatactors_App
////
////  Created by Anway Pimpalkar on 6/5/25.
////
//

import SwiftUI

struct DiscriminationPhaseView: View {
    @StateObject private var soundManager = SoundManager()
    @EnvironmentObject var appSettings: AppSettings
    @StateObject private var udpManager = UDPManager()
    @State private var trials: [DiscriminationTrial] = []
    @State private var currentTrialIndex = 0
    @State private var showBreakScreen = false
    @State private var selectedValveLevel = 0
    @State private var selectedPumpLevel = 0
    @State private var isStopped = false
    @State private var stimulusDelivered = false
    @State private var isStartButtonEnabled = false
    @State private var showSurveyScreen = false
    @State private var previousTrialType: String? = nil
    @State private var isSurveyButtonEnabled = false
    
    @State private var trialLog: [DiscriminationLogEntry] = []
    @State private var trialStartTime: Date = Date()

    let valveMapping = [0, 10, 20, 50, 100]
    let pumpMapping = [0, 200, 400, 700, 999]

    var body: some View {
        VStack(spacing: 30) {
            if showSurveyScreen {
                VStack(spacing: 20) {
                    Text("Time for a Survey!")
                        .font(.title)
                    
                    Text("The experimenter will open it for you.")
                        .font(.subheadline)

                    Button("Done") {
                        showSurveyScreen = false
                        previousTrialType = trials[currentTrialIndex].trial_type
                        showBreakScreen = true
                    }
                    .font(.headline)
                    .padding()
                    .background(isSurveyButtonEnabled ? Color.blue : Color.gray)
                    .foregroundColor(.white)
                    .cornerRadius(12)
                    .disabled(!isSurveyButtonEnabled)
                }
            } else if showBreakScreen {
                let nextTrialType = trials[currentTrialIndex].trial_type

                VStack(spacing: 10) {
                    Text("Trial \(currentTrialIndex + 1) of \(trials.count)")
                        .font(.headline)
                        .foregroundColor(.secondary)

                    Text({
                        switch nextTrialType {
                        case "pressure":
                            return "Identify: Pressure"
                        case "vibration":
                            return "Identify: Vibration"
                        case "multimodal":
                            return "Identify: Pressure + Vibration"
                        default:
                            return "Identification Task"
                        }
                    }())
                    .font(.title)
                    .fontWeight(.semibold)
                }
                Button("Start Trial") {
//                    showBreakScreen = false
//                    advanceTrial()
                    prepareNextTrial()
                }
                .font(.headline)
                .padding()
                .background(isStartButtonEnabled ? Color.blue : Color.gray)
                .foregroundColor(.white)
                .cornerRadius(12)
                .disabled(!isStartButtonEnabled)
                .onAppear {
                    isStartButtonEnabled = false
                    DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) {
                        isStartButtonEnabled = true
                    }
                }
            } else {
                if currentTrialIndex < trials.count {
                    let trial = trials[currentTrialIndex]
                    let trialType = trial.trial_type
                    
                    ZStack(alignment: .top) {
                        // ⏱ Time Remaining Button (top-left aligned)
                        HStack {
                            Button(action: {}) {
                                HStack {
                                    Image(systemName: "slowmo")
                                    Text("Trial \(trial.trial_number) of \(trials.count)")
                                }
                                .font(.subheadline)
                                .foregroundColor(.white)
                                .padding(.horizontal, 12)
                                .padding(.vertical, 8)
                                .frame(minWidth: 100) // match Stop All width visually
                                .background(Color(red: 0.1, green: 0.1, blue: 0.1))
                                .cornerRadius(8)
                            }
                            .disabled(true)
                            Spacer()
                        }
                        .padding([.top, .leading], 10)

                        
                        HStack {
                            Spacer()
                            
                            Button(action: {
                                stopAll()
                                isStopped = true
                            }) {
                                HStack {
                                    Image(systemName: "power")
                                        .foregroundColor(.white)
                                    Text("Stop")
                                        .font(.subheadline)
                                        .foregroundColor(.white)
                                }
                                .padding(.horizontal, 12)
                                .padding(.vertical, 8)
                                .frame(minWidth: 100)
                                .background(Color(red: 0.6, green: 0, blue: 0))
                                .cornerRadius(8)
                            }
                            
                        }
                        .padding([.top, .trailing], 10)
                    }
                    
                    Text({
                        switch trial.trial_type {
                        case "pressure":
                            return "Identify: Pressure"
                        case "vibration":
                            return "Identify: Vibration"
                        case "multimodal":
                            return "Identify: Pressure + Vibration"
                        default:
                            return "Identification Task"
                        }
                    }())
                    .font(.title)

                    Text({
                        switch trial.trial_type {
                        case "pressure":
                            return "Use the slider to select the pressure you felt."
                        case "vibration":
                            return "Use the slider to select the vibration you felt."
                        case "multimodal":
                            return "Use both sliders to select the combination you felt."
                        default:
                            return "Use the sliders to match the combination you feel."
                        }
                    }())
                    .font(.subheadline)

                    HStack(spacing: 50) {
                        VerticalSlider(
                            level: $selectedPumpLevel,
                            label: "Pressure",
                            mapping: pumpMapping,
                            color: Color(red: 0/255, green: 45/255, blue: 114/255),
                            showThumb: trialType != "vibration"
                        )
                        .disabled(trialType == "vibration")

                        VerticalSlider(
                            level: $selectedValveLevel,
                            label: "Vibration",
                            mapping: valveMapping,
                            color: Color(red: 104/255, green: 172/255, blue: 229/255),
                            showThumb: trialType != "pressure"
                        )
                        .disabled(trialType == "pressure")
                    }
                    
                    Button(action: {
                        stimulusDelivered = true
                        sendCurrentTrial(trials[currentTrialIndex])
                        DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) {
                            stopAll()
                            stimulusDelivered = false
                        }
                    }) {
                        Text("Replay")
                            .font(.headline)
                            .foregroundColor(.white)
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(stimulusDelivered ? Color.gray : Color(red: 203/255, green: 160/255, blue: 82/255))
                            .cornerRadius(12)
                            .padding(.horizontal)
                    }
                    .disabled(stimulusDelivered)
                    
                    Button(action: {
                        stopAll()
                        saveTrialLog(for: appSettings.selectedTrialFile.replacingOccurrences(of: "_trials.json", with: ""), trialNumber: trials[currentTrialIndex].trial_number)
                        if currentTrialIndex + 1 < trials.count {
                            currentTrialIndex += 1
                            showSurveyIfNeeded()
                            previousTrialType = trials[currentTrialIndex - 1].trial_type
                        } else {
                            currentTrialIndex += 1
                        }
                    }) {
                        Text("Submit")
                            .font(.headline)
                            .foregroundColor(.white)
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(selectedPumpLevel == 0 ? Color.gray : Color(red: 118/255, green: 160/255, blue: 76/255))
                            .cornerRadius(12)
                            .padding(.horizontal)
                    }
                    .disabled(selectedPumpLevel == 0)
                
                } else {
                    Text("Time for a Survey!")
                        .font(.title)
                    
                    Text("The experimenter will open it for you.")
                        .font(.subheadline)
                }
            }
        }
        .padding()
        .onAppear {
//            UIApplication.shared.isIdleTimerDisabled = true
            soundManager.playLoopingWhiteNoise()
            loadTrials()
        }
        .onChange(of: selectedValveLevel) { _ in logCurrent() }
        .onChange(of: selectedPumpLevel) { _ in logCurrent() }
        .navigationBarBackButtonHidden(true)
    }
    
    func showSurveyIfNeeded() {
        if currentTrialIndex < trials.count {
            let nextTrial = trials[currentTrialIndex]
            if let previous = previousTrialType, previous != nextTrial.trial_type {
                showSurveyScreen = true
                isSurveyButtonEnabled = false
                DispatchQueue.main.asyncAfter(deadline: .now() + 5) {
                    isSurveyButtonEnabled = true
                }
            } else {
                showBreakScreen = true
            }
        }
    }

    func loadTrials() {
        let filename = appSettings.selectedTrialFile
        let userID = filename.replacingOccurrences(of: "_trials.json", with: "")
        
        if let url = Bundle.main.url(forResource: filename, withExtension: nil) {
            do {
                let data = try Data(contentsOf: url)
                let decoded = try JSONDecoder().decode([DiscriminationTrial].self, from: data)
                trials = decoded
                
                // Resume if applicable
                let savedIndex = UserDefaults.standard.integer(forKey: "\(userID)_lastCompletedTrial")
                if savedIndex > 0 && savedIndex < trials.count {
                    currentTrialIndex = savedIndex
                    print("⏸️ Resuming from trial \(savedIndex + 1)")
                } else {
                    currentTrialIndex = 0
                }
                
                isStopped = false
                previousTrialType = trials[currentTrialIndex].trial_type
                showSurveyIfNeeded()
            } catch {
                print("❌ Failed to decode \(filename): \(error)")
            }
        } else {
            print("❌ File not found in bundle: \(filename)")
        }
    }


    func advanceTrial() {
        if currentTrialIndex < trials.count {
            let trial = trials[currentTrialIndex]

            selectedValveLevel = 0
            selectedPumpLevel = trial.trial_type == "vibration" ? trial.pressure_level : 0

            trialLog = []
            trialStartTime = Date()
            isStopped = false
            showBreakScreen = false
            stimulusDelivered = true
            previousTrialType = trial.trial_type

            sendCurrentTrial(trial)

            DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) {
                stopAll()
                stimulusDelivered = false
            }
        }
    }

    func prepareNextTrial() {
        if currentTrialIndex < trials.count {
            let nextTrial = trials[currentTrialIndex]
            if let previous = previousTrialType, previous != nextTrial.trial_type {
                showSurveyScreen = true
                isSurveyButtonEnabled = false
                DispatchQueue.main.asyncAfter(deadline: .now() + 5) {
                    isSurveyButtonEnabled = true
                }
            } else {
                advanceTrial()
            }
        }
    }
    
    func sendCurrentTrial(_ trial: DiscriminationTrial) {
        let valve = valveMapping[trial.vibration_level]
        let pump = pumpMapping[trial.pressure_level]
        udpManager.send(
            valve1: Double(valve),
            valve2: Double(valve),
            pump1: Double(pump),
            pump2: Double(pump)
        )
    }
    
    func stopAll() {
        udpManager.send(valve1: 0, valve2: 0, pump1: 0, pump2: 0)
    }
    
    func logCurrent() {
        let elapsed = Date().timeIntervalSince(trialStartTime)
        let trial = trials[currentTrialIndex]
        let entry = DiscriminationLogEntry(
            timestamp: elapsed,
            valve: valveMapping[selectedValveLevel],
            pump: pumpMapping[selectedPumpLevel],
            trial_type: trial.trial_type,
            delivered_pressure_level: trial.pressure_level,
            delivered_vibration_level: trial.vibration_level
        )
        trialLog.append(entry)
    }
    
    func saveTrialLog(for user: String, trialNumber: Int) {
        let fileManager = FileManager.default
        let directory = fileManager.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let userFolder = directory.appendingPathComponent(user)
        do {
            try fileManager.createDirectory(at: userFolder, withIntermediateDirectories: true)
            let fileURL = userFolder.appendingPathComponent("\(user)_trial\(trialNumber)_log.json")
            let data = try JSONEncoder().encode(trialLog)
            try data.write(to: fileURL)
            print("✅ Saved to \(fileURL)")
            
            // Save progress
            UserDefaults.standard.set(trialNumber, forKey: "\(user)_lastCompletedTrial")

        } catch {
            print("❌ Failed to save trial log: \(error)")
        }
    }
}

struct DiscriminationTrial: Codable, Identifiable {
    var id: Int { trial_number }
    let trial_number: Int
    let trial_type: String
    let pressure_level: Int
    let vibration_level: Int
}

struct DiscriminationLogEntry: Codable {
    let timestamp: TimeInterval
    let valve: Int
    let pump: Int
    let trial_type: String
    let delivered_pressure_level: Int
    let delivered_vibration_level: Int
}
