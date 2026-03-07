# Aquí irán los modelos de base de datos
# cuando agregues SQLAlchemy

class Producto:
    def __init__(self, nombre, precio):
        self.nombre = nombre
        self.precio = precio