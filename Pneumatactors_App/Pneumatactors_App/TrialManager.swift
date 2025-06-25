//
//  TrialManager.swift
//  Pneumatactors_App
//
//  Created by Anway Pimpalkar on 6/5/25.
//


import Foundation

class TrialManager: ObservableObject {
    @Published var trials: [Trial] = []
    @Published var currentIndex: Int = 0

    func loadTrials() {
        guard let url = Bundle.main.url(forResource: "trials", withExtension: "json"),
              let data = try? Data(contentsOf: url),
              let allTrials = try? JSONDecoder().decode([Trial].self, from: data) else {
//            print("Failed to load trials.json")
            return
        }

        trials = Array(repeating: allTrials, count: 5).flatMap { $0 }.shuffled()
        currentIndex = 0
    }


    var currentTrial: Trial? {
        guard currentIndex < trials.count else { return nil }
        return trials[currentIndex]
    }

    func nextTrial() {
        currentIndex += 1
    }

    var isComplete: Bool {
        return currentIndex >= trials.count
    }
}
