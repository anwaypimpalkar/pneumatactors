//
//  SoundManager.swift
//  Pneumatactors_App
//
//  Created by Anway Pimpalkar on 6/23/25.
//

import SwiftUI
import AVFoundation

class SoundManager: ObservableObject {
    private var audioPlayer: AVAudioPlayer?

    func playLoopingWhiteNoise() {
        guard let url = Bundle.main.url(forResource: "60Hz White Noise 1HR", withExtension: "mp3") else {
            print("❌ White noise file not found")
            return
        }

        do {
            audioPlayer = try AVAudioPlayer(contentsOf: url)
            audioPlayer?.numberOfLoops = -1  // 🔁 Loop indefinitely
            audioPlayer?.volume = 0.5        // Adjust volume as needed
            audioPlayer?.play()
            print("✅ White noise started")
        } catch {
            print("❌ Failed to play white noise: \(error)")
        }
    }

    func stop() {
        audioPlayer?.stop()
    }
}
