# 📡 Receptor PAM4 (RX) — Sincronización + Umbrales + Bits + Métricas

Este RX recibe una **trama PAM4** por red, se **sincroniza** con el preámbulo, calcula **umbrales adaptativos** (con EQ 1-tap), toma **decisiones de nivel**, **recupera los bits** del mensaje y genera **métricas locales**.  
Luego **reenvía** el texto y las métricas a la PC de **visualización**.

> Cubre la consigna del RX:
> **muestreo (digital por símbolo)** · **sincronización (correlación de preámbulo)** · **umbrales adaptativos** · **recuperación de bits** · **métricas locales (EVM/SNR/BER)**

---

## 🧠 Flujo del RX

1. **Escucha** por TCP (`0.0.0.0:5000`).
2. **Sincroniza** buscando el **preámbulo** (Barker-13 mapeado a ±3) mediante **correlación**.
3. Lee **40 pilotos** en orden `-3, -1, +1, +3`.
4. Estima **ganancia/offset** (`a`, `b`) con **ecualización 1-tap** y fija **umbrales adaptativos** `t1,t2,t3`.
5. **Decide** cada símbolo del **payload** y aplica **demapeo Gray**:
   - `00→-3`, `01→-1`, `11→+1`, `10→+3`
6. Reconstruye **bits → bytes → texto (UTF-8)**.
7. Calcula **EVM**, **SNR (estimada)** y **BER** (si definís `EXPECTED_TEXT`).
8. **Envía** un JSON al **visualizador** (UDP/TCP) con texto + métricas.

---
