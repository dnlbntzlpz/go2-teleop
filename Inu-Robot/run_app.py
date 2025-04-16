import sys
import os
from Inu_Robot.app import app

if __name__ == "__main__":
    print("Iniciando app...")
    app.run(host="0.0.0.0", port=8066)

# Agrega la ruta raíz del proyecto al PYTHONPATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Verifica que el path se agregó correctamente
print("PYTHONPATH:", sys.path)

# Ejecuta app.py manualmente
app_path = os.path.join(os.path.dirname(__file__), 'app.py')
with open(app_path, 'rb') as f:
    code = compile(f.read(), app_path, 'exec')
    exec(code, {'__name__': '__main__'})