import importlib
import pkgutil

def register_blueprints(app):
    package = __package__  # "endpoints"
    
    # Recorre recursivamente los subpaquetes dentro de "endpoints"
    for finder, name, ispkg in pkgutil.walk_packages(__path__, package + "."):
        try:
            module = importlib.import_module(f"{name}.routes")
            if hasattr(module, 'bp'):
                app.register_blueprint(module.bp)
                print(f"✅ Registrado blueprint: {name}")
        except ModuleNotFoundError:
            # No todos los subpaquetes tendrán un routes.py
            continue

    # Forzar importación del blueprint de caballos multiplayer si no se detecta automáticamente
    try:
        from .protected.api.juegos.multiplayer.caballos import routes as caballos_routes
        if hasattr(caballos_routes, 'bp'):
            app.register_blueprint(caballos_routes.bp)
            print("✅ Registrado blueprint: caballos multiplayer (forzado)")
    except Exception as e:
        print(f"❌ Error registrando blueprint caballos multiplayer: {e}")