<h1 align="center">
  <img src="plume_tracker/static/img/Logomark-BG-Red.svg" alt="Fly.io Logo" height="40" style="vertical-align: middle; margin-right: 10px;" />
   Plume Tracker
</h1>

> ⚠️ **Disclaimer**  
> Este proyecto es una iniciativa **comunitaria e independiente**.  
> **No es un producto oficial de Plume Network ni guarda relación alguna con su equipo.**  
> El uso de esta herramienta es únicamente con fines informativos y educativos.



Construí esta herramienta porque estaba harto de perder tiempo analizando wallets manualmente en Google Colab, APIs o directamente desde el [Leaderboard de Plume](https://portal.plume.org/leaderboard).  
Lo que empezó como simples scripts para mi [📒 Diario de un Farmer](https://github.com/IsmaelDatos/Diario_de_un_farmer/tree/main/Plume_network), se transformó en una web pensada para ayudar a otros farmers como yo.

👉 **Puedes probar la web aquí** 

➡️ **[Plume tracker](https://plume-tracker.fly.dev/)** ⬅️

## *"De un farmer, para farmers"* 

---

## 🙌 Gracias

Originalmente esta página estaba en **Vercel**, pero a los **3 días** tuvimos tantos usuarios que tuvimos que mudarnos a **Fly.io**. Nada mal. 
Estoy muy agradecido por el apoyo de la comunidad, porque este proyecto nació para uso personal y terminó creciendo mucho más de lo esperado.  

---

### Página Principal
![Index](plume_tracker/static/img/screenshot_index.png)  
En el index puedes ver la entrada principal a la web.

---

### Estadísticas de la Season 2

![Stats S2](plume_tracker/static/img/screenshot_s2Stats.png)  
Aquí se muestran las estadísticas de la Season 2, organizadas para facilitar el análisis.

---

### Detección de Sybils

![Sybils](/plume_tracker/static/img/screenshot_sybils.png)  

Cada burbuja representa una red de farming, y su tamaño corresponde al número de wallets vinculadas. Perfecto para identificar patrones sospechosos.Estos tramposos actuan de la siguiente forma, crean una wallet root,despues crean mas wallets y con el referido de la primera refieren n cantidad de wallets mas, posteriormente, toman el referido de las n wallets y se refieren mas wallets. No son muy listos a pesar de todo.

---

### Top Earners
![Top Earners](plume_tracker/static/img/screenshot_topearners.png)  
Con un clic puedes ver la tabla de **top earners**, ordenados y listos para revisar.

---

### Búsqueda de Wallets
![Wallet 1](plume_tracker/static/img/screenshot_wallet1.png)  
![Wallet 2](plume_tracker/static/img/screenshot_wallet2.png)  
Así se ve al consultar cualquier wallet. El usuario obtiene un desglose claro y visual de su información.

---

## 🛠️ Tecnologías Utilizadas

### Backend
<p align="left">
  <img align="center" alt="Flask" height="50" width="60" src="https://raw.githubusercontent.com/devicons/devicon/master/icons/flask/flask-original.svg">
  <img align="center" alt="Python" height="50" width="60" src="https://raw.githubusercontent.com/devicons/devicon/master/icons/python/python-original.svg">
</p>

### Frontend
<p align="left">
  <img align="center" alt="HTML5" height="50" width="60" src="https://raw.githubusercontent.com/devicons/devicon/master/icons/html5/html5-original.svg">
  <img align="center" alt="CSS3" height="50" width="60" src="https://raw.githubusercontent.com/devicons/devicon/master/icons/css3/css3-original.svg">
  <img align="center" alt="JavaScript" height="50" width="60" src="https://raw.githubusercontent.com/devicons/devicon/master/icons/javascript/javascript-original.svg">
  <img src="https://upload.wikimedia.org/wikipedia/commons/d/d5/Tailwind_CSS_Logo.svg" width="80" alt="Tailwind CSS">
</p>

### Infraestructura
<p align="left">
  <img align="center" alt="Fly.io" height="40" src="plume_tracker/static/img/logo-landscape-dark.png">
  <img align="center" alt="Git" height="50" width="60" src="https://raw.githubusercontent.com/devicons/devicon/master/icons/git/git-original.svg">
</p>

---

## 🚀 En constante mejora
Sigo optimizando esta herramienta mientras documento mi progreso en la Season 2 de Plume en:  
[📒 Diario de un Farmer - Plume Network](https://github.com/IsmaelDatos/Diario_de_un_farmer/tree/main/Plume_network)
