<!-- source: c1b2511ee47c687e -->

## Random New World

Un generador de Nuevos Mundos para Europa Universalis V. Rehace las Américas de arriba abajo: continentes, costas, relieve, clima, ríos, vegetación, recursos, provincias y pueblos nativos, y deja el Viejo Mundo tal como lo hizo Paradox. **Cada mundo que crea es un mod de mapa completo por sí mismo.** Se juega solo: guarda tantos mundos como quieras, bórralos o comparte el código de un mundo. El mundo se juega sin este generador, y cualquiera con la misma versión del juego obtiene el mismo mundo a partir de su código.

Este objeto no se activa en ninguna colección. Solo contiene el generador.

## Por qué este objeto trae un programa

EU5 construye su mapa a partir de archivos al cargar los mods. Un mod son datos: no puede ejecutar código. El script del juego puede decidir quién posee qué al empezar, pero no puede crear tierra, montañas ni ríos. EU5 no tiene ninguna vía oficial para añadir código al juego.

Por eso el mundo lo crea un pequeño programa que viene con este objeto. Lee tu instalación de EU5, crea un mundo y lo guarda como un mod corriente. No modifica el juego, no se engancha a él ni se ejecuta dentro. El acuerdo de usuario de Paradox incluye los programas entre los contenidos que los jugadores pueden crear y compartir gratis.

## Cómo se usa

1. En la ventana **Mods**, pulsa **Abrir en carpeta** en Random New World y haz doble clic en **Random New World Generator**.
2. Elige un tipo de mundo: supercontinente, continentes, continentes pequeños, archipiélago o islas dispersas. Deja la semilla aleatoria, escribe una o pega el código de un mundo. **Lo básico** responde con una palabra a las preguntas de siempre, como el Nuevo Mundo aleatorio de EU4: cuánta tierra, cuántos pueblos y estados nativos, con qué frecuencia surge un gran imperio nativo (nunca, rara vez, a veces, a menudo) y cuánto oro y plata hay. En **Personalizar** puedes cambiar cualquier valor: la tierra, las costas, la escala del mapa y los pueblos nativos, desde los grandes imperios hasta los estados aislados. Cualquier valor que se ofrece da un mundo jugable.
3. Pulsa **Crear**. En dos o tres minutos el mundo aparece como un mod nuevo en tu lista, con un nombre como «RNW: Small continents 7K3Q» (tipo de mundo y etiqueta); puedes cambiarle el nombre en el generador. Mientras el Nuevo Mundo está oculto, su imagen en la lista de mods lleva la misma etiqueta en rojo para distinguir los mundos.
4. En el juego, marca ese mundo (solo un mundo a la vez) y empieza una partida nueva. Si ya jugaste una campaña desde que abriste EU5, reinicia EU5 primero. El generador te dice exactamente qué hacer.

El generador guarda cada mundo que has creado, con su código. Mientras no decidas mostrarlo en **Ajustes**, el Nuevo Mundo sigue siendo terra incognita en todas partes antes de jugarlo: en las imágenes del generador, en la lista de mods del juego y en el mapa de la pantalla de partida nueva. Un solo ajuste lo desactiva todo. El código de un mundo recrea el mismo mundo, byte a byte, en cualquier ordenador con la misma versión del juego.

El generador habla todos los idiomas del juego y arranca en el que usa Steam para EU5.

## Qué hace el programa y qué no hace

- Lee tu instalación de EU5 y solo escribe en dos sitios: en los mundos que crea (`mod/rnw_world_…` en la carpeta de EU5 de tus Documentos) y en su propia carpeta de datos.
- No usa la red, no necesita permisos de administrador, no toca el registro y no cambia ningún archivo del juego.
- Su código fuente es público, con licencia Mozilla Public License 2.0: https://github.com/Sir-Starch/eu5-random-new-world. Cada versión se compila automáticamente a partir de un commit etiquetado, y allí se publica la suma de comprobación SHA-256 de cada archivo.
- Fiarte o no de un programa es decisión tuya. Puedes leer el código, comparar las sumas de comprobación o compilarlo tú mismo.

## Avisos de Windows

- Los archivos que descarga Steam no se marcan como procedentes de Internet, así que Windows SmartScreen no debería preguntar nada. [Confirm in 020.]
- A veces los antivirus dan la alarma con programas nuevos que aún no conocen. La página de cada versión enlaza un análisis de VirusTotal.
- El control inteligente de aplicaciones de Windows 11 bloquea los programas sin una firma conocida, y Windows no admite excepciones para programas concretos. [Until signed:] El generador aún no está firmado, así que con el control inteligente de aplicaciones activado no arrancará. [Once signed:] El generador y su módulo nativo están firmados por [signer].

## Linux y Steam Deck

El juego funciona con Proton. «Abrir en carpeta» abre entonces el explorador de archivos de Wine, y el mismo generador se ejecuta allí, dentro del prefijo de Proton del propio juego. No hace falta instalar nada. [Steam Deck: confirm.]

## Limitaciones

- **Solo campañas nuevas.** El mundo debe crearse antes de empezar la campaña.
- **Crea antes de jugar o reinicia.** EU5 se cuelga si, en la misma sesión, se inicia otro mundo después de una campaña (el fallo está en el motor del juego). Crear un mundo nada más abrir EU5 no requiere reiniciar; después de una campaña, reinicia EU5 antes del mundo nuevo.
- **Actualizaciones del juego.** Tras una actualización de EU5, puede que el generador se niegue a funcionar hasta que se adapte a la nueva versión. Entonces ofrece volver a crear tu mundo. Las partidas guardadas antiguas necesitan el mundo en el que se jugaron: vuelve a crearlo con su código.
- **Un mundo a la vez.** Marca solo un mundo creado en cada colección.
- **Multijugador.** Todos los jugadores usan el mismo código de mundo con la misma versión del juego.
- **Memoria.** Unos 7,5 GB de memoria libre durante los dos minutos de creación. Los 32 GB recomendados para EU5 sobran.
- **Logros.** Como otros mods que modifican el juego, cambia la suma de comprobación del juego. [Confirm what EU5 allows.]

## Cómo quitarlo

Borra los mundos en el generador (**Borrar mundo**) o elimina tú sus carpetas, y luego cancela la suscripción. Los mundos que conserves siguen siendo jugables sin el generador.

## Licencia y créditos

Código y archivos del mod: Mozilla Public License 2.0. Los mundos se crean en tu ordenador a partir de tu copia de EU5 y no se distribuyen por el Workshop. Europa Universalis V es una marca de Paradox Interactive; este mod no está afiliado a Paradox Interactive.
