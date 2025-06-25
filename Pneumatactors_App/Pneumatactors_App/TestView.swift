import SwiftUI

struct TestView: View {
    @State private var valve1 = 0.0
    @State private var valve2 = 0.0
    @State private var pump1 = 0.0
    @State private var pump2 = 0.0
    
    @State private var lastSentString: String = ""


    @StateObject private var udpManager = UDPManager()

    var body: some View {
        VStack {
            Text("Manual Control")
                .font(.title)
                .padding(.top)

            HStack(alignment: .center, spacing: 30) {
                VerticalSliderView(title: "Valve 1", value: $valve1, unit: "Hz", range: 0...120)
                    .onChange(of: valve1) { _ in sendValues() }

                VerticalSliderView(title: "Valve 2", value: $valve2, unit: "Hz", range: 0...120)
                    .onChange(of: valve2) { _ in sendValues() }

                VerticalSliderView(title: "Pump 1", value: $pump1, unit: "PWM", range: 0...999)
                    .onChange(of: pump1) { _ in sendValues() }

                VerticalSliderView(title: "Pump 2", value: $pump2, unit: "PWM", range: 0...999)
                    .onChange(of: pump2) { _ in sendValues() }
            }

            .padding()

            Spacer()

            Button(action: stopAll) {
                Text("Stop")
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.gray.opacity(0.8))
                    .foregroundColor(.white)
                    .cornerRadius(12)
                    .padding(.horizontal, 40)
            }
            .padding(.bottom, 20)
        }
        .navigationTitle("Test")
    }

    private func sendValues() {
        let message = String(format: "%03.0f%03.0f%03.0f%03.0f", valve1, valve2, pump1, pump2)
        if message != lastSentString {
            udpManager.send(valve1: valve1, valve2: valve2, pump1: pump1, pump2: pump2)
            lastSentString = message
        }
    }

    private func stopAll() {
        valve1 = 0
        valve2 = 0
        pump1 = 0
        pump2 = 0
        sendValues()
    }
}

struct VerticalSliderView: View {
    let title: String
    @Binding var value: Double
    let unit: String
    let range: ClosedRange<Double>

    var body: some View {
        VStack {
            Text(title)
                .font(.subheadline)

            ZStack {
                Slider(value: $value, in: range)
                    .rotationEffect(.degrees(-90))
                    .frame(width: 300)
                    .accentColor(.blue)
            }
            .frame(width: 40, height: 300)

            Text(String(format: "%03.0f %@", value, unit))
                .font(.caption)
                .foregroundColor(.gray)
        }
        .frame(width: 60)
    }
}

