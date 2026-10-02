# Regras de vencimento

Mesma lógica do painel (arquivo `vencimento.js` embutido nele). Em Python:

```python
from datetime import date, timedelta
import calendar
def util(d, fer): return d.weekday() < 5 and d.isoformat() not in fer
def aplica(ob, comp):
    m = int(comp[5:7])
    if ob.get("periodicidade") == "trimestral": return m % 3 == 0
    if ob.get("periodicidade") == "anual": return m == int(ob.get("mesBase") or 12)
    return True
def vencimento(ob, comp, feriados):
    if not aplica(ob, comp): return None
    fer = set(feriados or [])
    y, m = int(comp[:4]), int(comp[5:7]) + int(ob.get("mesOffset") or 0)
    y += (m - 1) // 12; m = (m - 1) % 12 + 1
    last = calendar.monthrange(y, m)[1]
    if ob["regra"] == "ultimo_util":
        d = date(y, m, last)
        while not util(d, fer): d -= timedelta(1)
        return d.isoformat()
    if ob["regra"] == "dia_util":
        d, n = date(y, m, 1), 0
        while True:
            if util(d, fer):
                n += 1
                if n >= int(ob.get("dia") or 1): return d.isoformat()
            d += timedelta(1)
    d = date(y, m, min(int(ob.get("dia") or 1), last))
    step = -1 if ob.get("ajuste") == "antecipa" else 1 if ob.get("ajuste") == "posterga" else 0
    while step and not util(d, fer): d += timedelta(step)
    return d.isoformat()
```

Casos de conferência: DAS 08/2026 → 21/09/2026 (dia 20 é domingo, prorroga). FGTS 08/2026 → 18/09/2026 (antecipa). EFD-Contribuições 08/2026 → 15/10/2026 (10º dia útil, com o feriado de 12/10).

Os feriados cadastrados são só os nacionais de 2026 e 2027. Se o usuário não tiver incluído os estaduais e municipais em Configurações, avise uma vez que os vencimentos de ICMS e ISS podem sair errados. Lembre também, no fim de cada ano, de incluir os feriados do ano seguinte.
