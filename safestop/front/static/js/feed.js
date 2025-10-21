// Como las imagenes se suben de forma asincronica no mostraremos nada de la tabla
// hasta que se carguen las imagenes
async function waitForImageToLoad2(imgPath, maxRetries = 50, interval = 500) {
    for (let i = 0; i < maxRetries; i++) {
        try {
            const res = await fetch("/safestop/front/api/check-image", {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ path: imgPath })
            });

            if (res.ok) {
                const img = await res.json();
                if (img.exists) 
                    return true;
            }

        } catch (e) {
            // Si hay un error, continuamos con el siguiente intento solamente
        }
        await new Promise(resolve => setTimeout(resolve, interval));
    }
    return false;
}

function tonum(time){
    return 60*(Number(time.substring(0, 2)))+(Number(time.substring(3, 5)));
}

function totime(num){
    let seconds = (num%60).toString();
    if(seconds.length===1){
        seconds="0"+seconds;
    }
    return Math.floor(num/60).toString()+":"+seconds;
}

// Aca guardaremos los fps, el intervalo del semaforo y el tiempo de inicio del video
let FPS = 0; 
let semaforo_interval = 0;
let time_start = 0;

// Ahora cargaremos asincronicamente el feed y luego se renderizara
window.addEventListener('DOMContentLoaded', async function() {
    // Obtenemos los elementos del html que cargaremos asincronicamente
    const video = this.document.getElementById('video');
    const id = this.window.feed_id;
    const loader = document.getElementById('loader');
    const div_video = document.getElementById('video_div');
    const div_semaforo = document.getElementById('semaforo_filter'); 
    const table = document.getElementById('resultTable');
    const table_body = document.getElementById('resultBody');

    // Ahora haremos la peticion
    try {
        // LLamamos a la api para obtener el feed
        const respone = await fetch(`/safestop/front/api/feed_stream${id}`, {
            method: 'GET',
        });

        // Si arroja un error lo mostramos
        if (!respone.ok) {
            loader.innerText = 'Error al cargar el feed'
            return;
        }

        // Si la respuesta es ok, vamos a ir leyendo el stream de datos a medida que llegan mediante un buffer
        const reader = respone.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        // Vamos a ir constantemente mostrando la tabla y recibiendo datos del stream
        while (true) {
            const { value, done } = await reader.read();
            if (done)
                break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop(); // Mantener la última línea incompleta en el buffer

            for (let line of lines) {
                if (!line.trim()) continue; // Ignorar líneas vacías

                const data = JSON.parse(line);

                // Si es un error terminamos el bucle
                if (data.error) {
                    loader.innerText = 'Error al cargar el feed: ' + data.error;
                    break;
                }

                // Si es que llegan los datos especiales del video, los guardamos y mostramos el video
                if (data.video_info) {

                    // Y guardamos los fps, el intervalo del semaforo y el tiempo de inicio del video
                    FPS = data.video_info.fps;
                    semaforo_interval = data.video_info.semaforo_interval;
                    time_start = data.video_info.creation_time;

                    // Y mostramos el video
                    video.innerHTML = `<source src="/safestop/front/static/video/${data.video_info.name}" type="video/mp4">`;
                    video.load();
                    video.play();
                    video.addEventListener('ended', function() {
                        video.pause();
                        video.currentTime = 0;
                    });
                    // Y mostramos la tabla y todo lo demas
                    loader.style.display = 'none';
                    div_video.style.display = 'flex';
                    table.style.display = 'table';

                    continue; // Continuamos con la siguiente línea
                }

                // Ahora si no tiene los FPS asumimos es un frame del feed
                const frame = data

                // Apenas conseguimos un frame vamos a esperar a que las imagenes se carguen
                await waitForImageToLoad2(frame.plate_crop);
                await waitForImageToLoad2(frame.frame);

                // Luego armamos toda la fila
                const tr = document.createElement('tr');

                const td_date = document.createElement('td');
                td_date.textContent = frame.date;

                const td_time = document.createElement('td');
                td_time.textContent = totime((Math.floor(frame.frame_count / FPS)) + tonum(time_start));

                const td_image = document.createElement('td');
                const img = document.createElement('img');
                img.style.width = '300px';
                img.style.height = '250px';
                img.src = `/safestop/front/static/img/${frame.plate_crop}`;
                td_image.appendChild(img);

                const td_frame = document.createElement('td');
                const img2 = document.createElement('img');
                img2.style.width = '300px';
                img2.style.height = '250px';
                img2.src = `/safestop/front/static/img/${frame.frame}`;
                td_frame.appendChild(img2);

                const td_patent = document.createElement('td');
                td_patent.textContent = frame.patent;

                const td_semaforo = document.createElement('td');
                td_semaforo.textContent = frame.semaforo;

                const td_back = document.createElement('td');
                const a_verButton = document.createElement('a');
                a_verButton.textContent = 'ver';
                a_verButton.classList.add('verButton');
                a_verButton.onclick = function() {
                    jump(frame.frame_count / FPS);
                };
                td_back.appendChild(a_verButton);

                // Ahora le damos mas color a la fila dependiendo del semáforo
                if (frame.semaforo === 'Verde') {
                    tr.style.backgroundColor = 'rgba(0,150,0,0.2)';
                    a_verButton.classList.add('verButton', 'verde');
                } else if (frame.semaforo === 'Rojo') {
                    tr.style.backgroundColor = 'rgba(150,0,0,0.3)';
                    a_verButton.classList.add('verButton', 'rojo');
                    // Aca si tenemos semaforos en rojo mostramos el boton de filtro
                    div_semaforo.style.display = 'block';
                } else {
                    tr.style.backgroundColor = 'rgba(150,150,0,0.001)';
                }

                tr.appendChild(td_date);
                tr.appendChild(td_time);
                tr.appendChild(td_image);
                tr.appendChild(td_frame);
                tr.appendChild(td_patent);
                tr.appendChild(td_semaforo);
                tr.appendChild(td_back);
                table_body.appendChild(tr);
            }
        }
    } catch (error) {
        loader.innerText = 'Error al cargar el feed: ' + error;
    }
});

// Guardamos las fotos en memoria para no tener que cargarlas cada vez que cambiamos el semáforo
const semaforoImages = {
    verde: new Image(),
    rojo: new Image()
};

semaforoImages.verde.src = SEMAFORO_VERDE_URL;
semaforoImages.rojo.src = SEMAFORO_ROJO_URL;

var myVideo = document.getElementById("video");
var liveButton = document.getElementById("liveButton");
var semaforo = document.getElementById("semaforo");
let liveTime=0;
let lastJump=0;
let realTime=0;
let timeOffset=0;

myVideo.ontimeupdate = function() {setSemaforo()};

function setSemaforo(){
    if (Math.floor(myVideo.currentTime/semaforo_interval)% 2 === 0)
        semaforo.src=semaforoImages.verde.src;
    else 
        semaforo.src=semaforoImages.rojo.src;
}

function jump(x) {
    liveButton.style.visibility = "visible";
    if (realTime===1){
        timeOffset = timeOffset+myVideo.currentTime-lastJump;
    }
    else {
        liveTime=myVideo.currentTime;
        realTime=1;
    }
    lastJump=x-1;
    myVideo.currentTime = x-1;
    document.documentElement.scrollTop = 0;
    myVideo.play();
}

function live(){
    liveButton.style.visibility = "hidden";
    if (realTime===1){
        timeOffset += myVideo.currentTime-lastJump;
        liveTime += timeOffset;
        timeOffset=0
        myVideo.currentTime=liveTime;
        realTime=0;
        document.documentElement.scrollTop = 0;
        myVideo.play();
    }
}

// Finalmente tendremos una funciona para filtrar solo los frames que esten en rojo
let filtroRojoActivo = false;

function toggleSemaforoFilter() {
    const tabla = document.getElementById('resultBody');
    const filas = tabla.querySelectorAll('tr');
    const boton = document.getElementById('semaforoFilterButton');

    filtroRojoActivo = !filtroRojoActivo;

    if (filtroRojoActivo) {
        boton.classList.add('verButton', 'rojo');
        filas.forEach(fila => {
            const celdaSemaforo = fila.cells[5]?.textContent.trim();
            if (celdaSemaforo !== 'Rojo') {
                fila.style.display = "none";
            }
        });
    } else {
        boton.classList.remove('rojo');
        filas.forEach(fila => {
            fila.style.display = "";
        });
    }
};