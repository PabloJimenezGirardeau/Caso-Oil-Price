"""Genera data/dias_brent.csv: los días en que el Brent cotizó de verdad (D13).

El CSV de datos rellena los festivos del Brent con el precio del día anterior. Para
distinguir los días reales sin depender de internet en cada ejecución, este script
descarga una vez de FRED la serie original (DCOILBRENTEU, sin rellenar) y guarda sus
fechas.

Uso:
    poetry run python scripts/generar_dias_brent.py
"""
from oil_price.config import RUTA_DIAS_BRENT

import pandas as pd

URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DCOILBRENTEU&cosd=2000-01-01"


def main():
    serie = pd.read_csv(URL, index_col=0, parse_dates=True, na_values=".").iloc[:, 0].dropna()
    dias = pd.DataFrame({"Date": serie.index.strftime("%Y-%m-%d")})
    dias.to_csv(RUTA_DIAS_BRENT, index=False)
    print(f"{len(dias):,} días de cotización ({dias['Date'].iloc[0]} → {dias['Date'].iloc[-1]}) "
          f"guardados en {RUTA_DIAS_BRENT}")


if __name__ == "__main__":
    main()
