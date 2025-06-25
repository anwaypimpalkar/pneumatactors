import SwiftUI

struct TrainingPhaseView: View {
    @StateObject private var soundManager = SoundManager()
    @EnvironmentObject var appSettings: AppSettings
    @EnvironmentObject var trialManager: TrialManager
    @Binding var trainingComplete: Bool
    @State private var timeRemaining: Int = 5
    @State private var shouldNavigateToTask = false
    @State private var showInstructions = true
    @StateObject private var udpManager = UDPManager()
    
    @State private var log: [TrainingLogEntry] = []
    @State private var trainingStartTime: Date = Date()

    @State private var valveLevel = 0
    @State private var pumpLevel = 0
    
    @State private var stimulusDelivered = false

    let valveMapping = [0, 10, 20, 50, 100]
    let pumpMapping = [0, 200, 400, 700, 999]

    var body: some View {
        VStack(spacing: 30) {
            if showInstructions {
                Text("Training Instructions")
                    .font(.title)
                    .bold()
                    .padding(.bottom, 8)

                VStack(alignment: .leading, spacing: 16) {
                    HStack(alignment: .top, spacing: 12) {
                        Image(systemName: "waveform.path.ecg")
                            .foregroundColor(.blue)
                        Text("Explore combinations of vibration and pressure using the sliders.")
                    }

                    HStack(alignment: .top, spacing: 12) {
                        Image(systemName: "slider.horizontal.3")
                            .foregroundColor(.orange)
                        Text("Move sliders to feel different intensity levels.")
                    }

                    HStack(alignment: .top, spacing: 12) {
                        Image(systemName: "questionmark.circle")
                            .foregroundColor(.purple)
                        Text("In the task, you'll identify which combination you felt.")
                    }

                    HStack(alignment: .top, spacing: 12) {
                        Image(systemName: "clock")
                            .foregroundColor(.red)
                        Text("You have \(timeRemaining) seconds to explore before the task begins.")
                    }

                    HStack(alignment: .top, spacing: 12) {
                        Image(systemName: "play.circle")
                            .foregroundColor(.green)
                        Text("Tap 'Start Training' when you're ready.")
                    }
                }
                .font(.body)
                .padding()
                .background(Color(UIColor.systemGray6))
                .cornerRadius(12)
                .padding(.horizontal)
                .onAppear {
                    soundManager.playLoopingWhiteNoise()
                }
                Button("Start Training") {
                    showInstructions = false
                    startTimer()
                }
                .font(.headline)
                .padding()
                .background(Color.blue)
                .foregroundColor(.white)
                .cornerRadius(12)
            } else {
                ZStack(alignment: .top) {
                    // ⏱ Time Remaining Button (top-left aligned)
                    HStack {
                        Button(action: {}) {
                            HStack {
                                Image(systemName: "clock")
                                Text("\(timeRemaining) sec")
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

                    // 🟥 Stop All Button (top-right aligned)
                    HStack {
                        Spacer()
                        Button(action: {
                            valveLevel = 0
                            pumpLevel = 0
                            sendCurrentLevels()
                        }) {
                            HStack {
                                Image(systemName: "power")
                                    .foregroundColor(.white)
                                Text("Stop")
                                    .font(.subheadline)
                                    .foregroundColor(.white)
                                }
                                .font(.subheadline)
                                .foregroundColor(.white)
                                .padding(.horizontal, 12)
                                .padding(.vertical, 8)
                                .frame(minWidth: 100)
                                .background(Color(red: 0.6, green: 0, blue: 0))
                                .cornerRadius(8)
                        }
                    }
                    .padding([.top, .trailing], 10)
                }


                // 🎯 Main Training Interface
                Text("Training Phase")
                    .font(.title)

                Text("Explore combinations of pressure and vibration freely.")
                    .font(.subheadline)

                HStack(spacing: 50) {
                    VerticalSlider(
                        level: $pumpLevel,
                        label: "Pressure",
                        mapping: pumpMapping,
                        color: Color(red: 0/255, green: 45/255, blue: 114/255),
                        onRelease: sliderReleased
                    )

                    VerticalSlider(
                        level: $valveLevel,
                        label: "Vibration",
                        mapping: valveMapping,
                        color: Color(red: 104/255, green: 172/255, blue: 229/255),
                        onRelease: sliderReleased
                    )
                }
                
                
                Button(action: {
                    stimulusDelivered = true
                    sendCurrentLevels() // You likely meant this instead of sendCurrentTrial()

                    DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) {
                        udpManager.send(valve1: 0, valve2: 0, pump1: 0, pump2: 0) // ⛔️ Not stopAll()
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
                
                Text("Set a non-zero pressure to render vibration.")
                    .font(.subheadline)
                    .opacity((valveLevel > 0 && pumpLevel == 0) ? 1 : 0)
                

                Button(action: {
                    valveLevel = 0
                    pumpLevel = 0
                    sendCurrentLevels()
                }) {
                    Text("Submit")
                        .font(.headline)
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color(red: 0, green: 0.6, blue: 0)) // Dark red
                        .cornerRadius(12)
                        .padding(.horizontal)
                }
                .disabled(true)
                .opacity(0)
            
                
                NavigationLink(
                    destination: DiscriminationPhaseView().environmentObject(trialManager),
                    isActive: $shouldNavigateToTask,
                    label: { EmptyView() }
                )
            }
        }
        .padding()
        .onAppear {
            if trialManager.trials.isEmpty {
                trialManager.loadTrials()
            }
            trainingStartTime = Date()

            print("🧩 Selected trial file: \(appSettings.selectedTrialFile)")
        }
        .onDisappear {
            let selectedFile = appSettings.selectedTrialFile
            let user = selectedFile
                .replacingOccurrences(of: "_trials.json", with: "")
                .replacingOccurrences(of: ".json", with: "")
            saveTrainingLog(for: user)
            UserDefaults.standard.set(true, forKey: "\(user)_trainingComplete")
        }
//        .onChange(of: valveLevel) { _ in sendCurrentLevels() }
//        .onChange(of: pumpLevel) { _ in sendCurrentLevels() }
        .onChange(of: trainingComplete) { newValue in
            if newValue {
                shouldNavigateToTask = true
            }
        }
        .navigationBarBackButtonHidden(true)
    }

    func sendCurrentLevels() {
        let valveValue = valveMapping[valveLevel]
        let pumpValue = pumpMapping[pumpLevel]
        udpManager.send(
            valve1: Double(valveValue),
            valve2: Double(valveValue),
            pump1: Double(pumpValue),
            pump2: Double(pumpValue)
        )
        let timeElapsed = Date().timeIntervalSince(trainingStartTime)
        log.append(TrainingLogEntry(timestamp: timeElapsed, valve: valveValue, pump: pumpValue))
    }

    func startTimer() {
        Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { timer in
            if timeRemaining > 0 {
                timeRemaining -= 1
            } else {
                timer.invalidate()
                udpManager.send(valve1: 0, valve2: 0, pump1: 0, pump2: 0)
                let user = appSettings.selectedTrialFile.replacingOccurrences(of: "_trials.json", with: "")
                saveTrainingLog(for: user)
                trainingComplete = true
            }
        }
    }
    
    func saveTrainingLog(for user: String) {
        let documentsURL = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let userFolder = documentsURL.appendingPathComponent(user)

        do {
            try FileManager.default.createDirectory(at: userFolder, withIntermediateDirectories: true)
            let fileURL = userFolder.appendingPathComponent("\(user)_training.json")

            let data = try JSONEncoder().encode(log)
            try data.write(to: fileURL)
            print("✅ Training log saved to \(fileURL)")
        } catch {
            print("❌ Failed to save training log: \(error)")
        }
    }
    
    func sliderReleased() {
        sendCurrentLevels()
        DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) {
            udpManager.send(valve1: 0, valve2: 0, pump1: 0, pump2: 0)
            stimulusDelivered = false
        }
        stimulusDelivered = true
    }
}



//struct VerticalSlider: View {
//    @Binding var level: Int
//    let label: String
//    let mapping: [Int]
//    let color: Color
//    let sliderHeight: CGFloat = 250
//    let levels = 5
//
//    var body: some View {
//        VStack(spacing: 30) {
//            VStack(spacing: 2) {
//                Text(label)
//                    .font(.headline)
//                Text(level == 0 ? "Off" : "Level \(level)")
//                    .font(.subheadline)
//                    .foregroundColor(.gray)
//            }
//
//
//            ZStack(alignment: .bottom) {
//                // Triangle background
//                Triangle()
//                    .fill(LinearGradient(
//                        gradient: Gradient(colors: [color.opacity(0.2), color]),
//                        startPoint: .bottom,
//                        endPoint: .top
//                    ))
//                    .frame(width: 30, height: sliderHeight)
//
//                // Growing thumb
//                GeometryReader { geo in
//                    let totalHeight = geo.size.height
//                    let step = totalHeight / CGFloat(levels - 1)
//                    let yPos = totalHeight - CGFloat(level) * step
//
//                    Circle()
//                        .fill(level == 0 ? Color.gray : Color.white)
//                        .frame(width: 20 + CGFloat(level * 6), height: 20 + CGFloat(level * 6))
//                        .shadow(radius: 3)
//                        .position(x: geo.size.width / 2, y: yPos)
//                        .gesture(
//                            DragGesture()
//                                .onChanged { value in
//                                    let newLevel = max(0, min(levels - 1,
//                                        Int(round((totalHeight - value.location.y) / step))
//                                    ))
//                                    if newLevel != level {
//                                        level = newLevel
//                                    }
//                                }
//                        )
//                }
//                .frame(width: 50, height: sliderHeight)
//            }
//        }
//    }
//}


struct VerticalSlider: View {
    @Binding var level: Int
    let label: String
    let mapping: [Int]
    let color: Color
    let sliderHeight: CGFloat = 250
    let levels = 5
    var onRelease: (() -> Void)? = nil
    var showThumb: Bool = true

    var body: some View {
        VStack(spacing: 30) {
            VStack(spacing: 2) {
                Text(label)
                    .font(.headline)
                Text(level == 0 ? "Off" : "Level \(level)")
                    .font(.subheadline)
                    .foregroundColor(.gray)
            }

            ZStack(alignment: .bottom) {
                Triangle()
                    .fill(LinearGradient(
                        gradient: Gradient(colors: [color.opacity(0.2), color]),
                        startPoint: .bottom,
                        endPoint: .top
                    ))
                    .frame(width: 30, height: sliderHeight)

                GeometryReader { geo in
                    let totalHeight = geo.size.height
                    let step = totalHeight / CGFloat(levels - 1)
                    let yPos = totalHeight - CGFloat(level) * step
                    if showThumb {
                        Circle()
                            .fill(level == 0 ? Color.gray : Color.white)
                            .frame(width: 20 + CGFloat(level * 6), height: 20 + CGFloat(level * 6))
                            .shadow(radius: 3)
                            .position(x: geo.size.width / 2, y: yPos)
                            .gesture(
                                DragGesture()
                                    .onChanged { value in
                                        let newLevel = max(0, min(levels - 1,
                                                                  Int(round((totalHeight - value.location.y) / step))
                                                                 ))
                                        if newLevel != level {
                                            level = newLevel
                                        }
                                    }
                                    .onEnded { _ in
                                        onRelease?()
                                    }
                            )
                    }
                }
                .frame(width: 50, height: sliderHeight)
            }
        }
    }
}


struct Triangle: Shape {
    func path(in rect: CGRect) -> Path {
            var path = Path()
            path.move(to: CGPoint(x: rect.midX, y: rect.maxY))       // bottom center
            path.addLine(to: CGPoint(x: rect.minX, y: rect.minY))    // top left
            path.addLine(to: CGPoint(x: rect.maxX, y: rect.minY))    // top right
            path.closeSubpath()
            return path
        }
}


struct TrainingLogEntry: Codable {
    let timestamp: TimeInterval
    let valve: Int
    let pump: Int
}
