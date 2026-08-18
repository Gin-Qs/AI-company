"""Capa deterministica de la Oficina Virtual (arquitectura v3, seccion 6).

Ningun modulo de este paquete llama a un LLM. Todo lo que vive aqui es
codigo testeable: calcula, valida y normaliza. Los agentes consumen estos
servicios como herramientas; nunca replican su aritmetica.
"""
