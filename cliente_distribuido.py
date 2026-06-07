#!/usr/bin/env python3
"""
Cliente para PFO 3 - Envía tareas al servidor distribuido
"""

import socket
import json
import time
import sys
import hashlib

HOST = 'localhost'
PORT = 5000
BUFFER_SIZE = 4096


class ClienteDistribuido:
    def __init__(self):
        self.socket_cliente = None

    def conectar(self):
        self.socket_cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_cliente.connect((HOST, PORT))

    def desconectar(self):
        if self.socket_cliente:
            self.socket_cliente.close()

    def enviar_tarea(self, tarea: dict) -> dict:
        """Envía una tarea al servidor y espera respuesta"""
        try:
            self.conectar()
            datos = json.dumps(tarea)
            self.socket_cliente.send(datos.encode('utf-8'))
            respuesta = self.socket_cliente.recv(BUFFER_SIZE).decode('utf-8')
            return json.loads(respuesta)
        finally:
            self.desconectar()

    def consultar_estado(self, tarea_id: str) -> dict:
        """Consulta el estado de una tarea (simulado, para demostración)"""
        tarea = {'tipo': 'consulta', 'id': tarea_id}
        return self.enviar_tarea(tarea)


def menu():
    print("\n" + "=" * 50)
    print(" CLIENTE DISTRIBUIDO - PFO 3")
    print("=" * 50)
    print("1. Enviar texto para calcular hash SHA-256")
    print("2. Enviar texto para contar caracteres")
    print("3. Enviar archivo (simulado como texto)")
    print("4. Salir")
    print("=" * 50)


def main():
    cliente = ClienteDistribuido()

    while True:
        menu()
        opcion = input("Seleccione una opción: ").strip()

        if opcion == '1':
            texto = input("Ingrese el texto a hashear: ")
            tarea = {
                'tipo': 'hash',
                'datos': texto
            }
            respuesta = cliente.enviar_tarea(tarea)
            print(f"✅ Respuesta del servidor: {respuesta}")

        elif opcion == '2':
            texto = input("Ingrese el texto a contar: ")
            tarea = {
                'tipo': 'contar',
                'datos': texto
            }
            respuesta = cliente.enviar_tarea(tarea)
            print(f"✅ Respuesta del servidor: {respuesta}")

        elif opcion == '3':
            texto = input("Ingrese el contenido del archivo (simulado): ")
            tarea = {
                'tipo': 'archivo',
                'datos': texto
            }
            respuesta = cliente.enviar_tarea(tarea)
            print(f"✅ Respuesta del servidor: {respuesta}")

        elif opcion == '4':
            print(" ¡Hasta luego!")
            break

        else:
            print("❌ Opción inválida")

        # Pequeña pausa para ver resultado
        if opcion in ['1', '2', '3']:
            print("\n💡 Las tareas se procesan en segundo plano por los workers.")
            print("   Podés consultar la base de datos 'tareas.db' para ver resultados.")


if __name__ == '__main__':
    main()