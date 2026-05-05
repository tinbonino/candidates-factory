"""
Genera el hash bcrypt de una contraseña para agregar en Streamlit Secrets.
Uso: python generate_password_hash.py

Nota: con auto_hash=True en streamlit-authenticator 0.4.x podés poner
la contraseña en texto plano en los Secrets — se hashea automáticamente
al primer login. Este script es útil si preferís pre-hashear las passwords.
"""
import bcrypt

password = input("Ingresá la contraseña: ").strip()
hashed   = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

print(f"\nHash generado:\n{hashed}")
print("\nAgregalo en Streamlit Secrets así:")
print(f'password = "{hashed}"')
