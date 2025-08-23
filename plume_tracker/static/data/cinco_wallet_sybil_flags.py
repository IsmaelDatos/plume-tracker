import json

def procesar_archivo_sybil():
    ruta_entrada = "/home/ismael/Desktop/plume-tracker/plume_tracker/static/data/plume_wallets_enriched.json"
    ruta_salida = "/home/ismael/Desktop/plume-tracker/plume_tracker/static/data/wallet_search_sybil.json"
    
    try:
        with open(ruta_entrada, 'r') as archivo:
            datos = json.load(archivo)
        
        datos_simplificados = []
        for item in datos:
            if "walletAddress" in item and "sybilFlag" in item:
                datos_simplificados.append({
                    "walletAddress": item["walletAddress"],
                    "sybilFlag": item["sybilFlag"]
                })
        with open(ruta_salida, 'w') as archivo_salida:
            json.dump(datos_simplificados, archivo_salida, indent=2)
        
        print(f"Archivo procesado exitosamente!")
        print(f"Se guardaron {len(datos_simplificados)} registros en {ruta_salida}")
        
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo en la ruta {ruta_entrada}")
    except json.JSONDecodeError:
        print("Error: El archivo no tiene un formato JSON válido")
    except Exception as e:
        print(f"Error inesperado: {str(e)}")

if __name__ == "__main__":
    procesar_archivo_sybil()