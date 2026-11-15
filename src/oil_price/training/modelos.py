"""Modelos: las tres redes recurrentes y el modelo lineal de referencia (D11, D16, D17).

Las tres redes comparten exactamente la misma estructura; solo cambia la celda recurrente.
Así, si una gana, es por su tipo de memoria y no por otra diferencia (requisito 5).
"""
import numpy as np
import torch
from torch import nn

TIPOS_CELDA = {"RNN": nn.RNN, "LSTM": nn.LSTM, "GRU": nn.GRU}


class RedRecurrente(nn.Module):
    """ficha (ventana × variables) → celda recurrente → dropout → capa lineal → una salida por horizonte."""

    def __init__(self, celda, n_entradas, unidades=64, capas=1, dropout=0.0, n_salidas=3):
        super().__init__()
        self.celda = celda
        self.recurrente = TIPOS_CELDA[celda](
            n_entradas, unidades, num_layers=capas, batch_first=True,
            dropout=dropout if capas > 1 else 0.0)  # dropout entre capas recurrentes
        self.dropout = nn.Dropout(dropout)               # dropout antes de la salida
        self.salida = nn.Linear(unidades, n_salidas)

    def forward(self, x):
        secuencia, _ = self.recurrente(x)
        return self.salida(self.dropout(secuencia[:, -1]))  # estado del último día de la ventana


def contar_parametros(modelo):
    return sum(p.numel() for p in modelo.parameters() if p.requires_grad)


class ModeloLineal:
    """Regresión lineal con regularización (Ridge) sobre la ficha aplanada (D17).

    Peldaño intermedio entre el ingenuo (no aprende) y las redes (relaciones complejas):
    cada valor de la ficha suma o resta con un peso fijo. Se ajusta un modelo por horizonte,
    usando solo las fichas con respuesta válida.

    Con `sin_tendencia` (D20), el término fijo es cero en lugar de la subida media del train:
    con una ficha «media», prevé que el precio no cambia, como el ingenuo. Los pesos no cambian.
    """

    def __init__(self, alfa=100.0, sin_tendencia=False):
        self.alfa = alfa
        self.sin_tendencia = sin_tendencia

    def ajustar(self, conjunto):
        X = conjunto.X.reshape(len(conjunto), -1).astype(np.float64)
        self.media_x_, self.coef_, self.intercepto_ = [], [], []
        for j in range(conjunto.Y.shape[1]):
            validas = ~np.isnan(conjunto.Y[:, j])
            Xj, yj = X[validas], conjunto.Y[validas, j].astype(np.float64)
            media_x = Xj.mean(axis=0)
            Xc = Xj - media_x
            coef = np.linalg.solve(Xc.T @ Xc + self.alfa * np.eye(Xc.shape[1]), Xc.T @ (yj - yj.mean()))
            self.media_x_.append(media_x)
            self.coef_.append(coef)
            self.intercepto_.append(0.0 if self.sin_tendencia else yj.mean())
        return self

    def predecir(self, X):
        X = X.reshape(len(X), -1).astype(np.float64)
        return np.column_stack([(X - m) @ c + b for m, c, b
                                in zip(self.media_x_, self.coef_, self.intercepto_)]).astype(np.float32)

    @property
    def n_parametros(self):
        return int(sum(c.size + (0 if self.sin_tendencia else 1) for c in self.coef_))
