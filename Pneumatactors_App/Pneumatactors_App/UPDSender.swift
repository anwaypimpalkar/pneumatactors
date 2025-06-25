//
//  UPDSender.swift
//  Pneumatactors_App
//
//  Created by Anway Pimpalkar on 6/4/25.
//

import Foundation
import Network

class UDPSender {
    private var connection: NWConnection?
    private var host: NWEndpoint.Host
    private var port: NWEndpoint.Port

    init?(host: String, port: String) {
        guard let portUInt = UInt16(port) else { return nil }
        self.host = NWEndpoint.Host(host)
        self.port = NWEndpoint.Port(rawValue: portUInt)!
        setupConnection()
    }

    private func setupConnection() {
        connection = NWConnection(host: host, port: port, using: .udp)
        connection?.start(queue: .global())
    }

    func send(_ message: String) {
        let data = message.data(using: .utf8) ?? Data()
        connection?.send(content: data, completion: .contentProcessed { error in
            if let error = error {
                print("UDP send error: \(error)")
            } else {
                print("Sent: \(message)")
            }
        })
    }
}

class UDPManager: ObservableObject {
    private var sender: UDPSender?

    init() {
        loadConfig()
    }

    func loadConfig() {
        let ip = UserDefaults.standard.string(forKey: "ipAddress") ?? "192.168.4.1"
        let port = UserDefaults.standard.string(forKey: "port") ?? "4210"
        sender = UDPSender(host: ip, port: port)
    }

    func send(valve1: Double, valve2: Double, pump1: Double, pump2: Double) {
        let str = String(format: "%03.0f%03.0f%03.0f%03.0f", valve1, valve2, pump1, pump2)
        sender?.send(str)
    }
}

