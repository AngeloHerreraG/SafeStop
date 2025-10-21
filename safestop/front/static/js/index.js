// Definimos una funcion para el reincio de los datos, tiene una contraseña para evitar 
// que cualquier usuario pueda reiniciar los datos
document.addEventListener("DOMContentLoaded", () => {

    // Lo primero es ver si es que eixste todo el formulario de reinicio
    const checkReset = document.getElementById("reseted");

    // Si no existe el formulario por que no se ha hecho una petición GET a la ruta de reinicio
    // entonces no hacemos nada
    if (!checkReset) {
        console.log("Formulario de reinicio no encontrado, no se cargará el modal.");
        return;
    }

    // Obtenemos algunos elementos del modal
    const modal = document.getElementById("resetModal");
    const confirmBtn = document.getElementById("confirmReset");
    const cancelBtn = document.getElementById("cancelReset");
    const inputPass = document.getElementById("passwordInput");
    const errorMsg = document.getElementById("errorMsg");
    const successMsg = document.getElementById("successMsg");

    if (!modal || !confirmBtn || !cancelBtn || !inputPass || !errorMsg || !successMsg) {
        console.warn("Faltan elementos del modal.");
        return;
    }

    // Si el modal esta cargado, lo mostramos y limpiamos los mensajes
    inputPass.value = "";
    errorMsg.style.display = "none";
    successMsg.style.display = "none";
    inputPass.focus();

    // Sanitizamos el input para mejor UI/UX
    inputPass.addEventListener("input", () => {
        // Solo permitimos letras y números, no espacios ni caracteres especiales
        inputPass.value = inputPass.value.replace(/[^a-zA-Z0-9]/g, "");
        // Y la contraseña tiene largo maximo de 20 caracteres
        inputPass.value = inputPass.value.slice(0, 20);
        // Resaltamos el borde si está vacío
        // Esto es para mejorar la experiencia del usuario
        if (inputPass.value === "") {
            inputPass.style.borderColor = "red"; 
        } else {
            inputPass.style.borderColor = "#ccc";
        }
    });

    // Si cancelamos la accion, redirigimos al index
    // Esto es para evitar que el usuario se quede en la pagina de reinicio
    cancelBtn.addEventListener("click", () => {
        modal.style.display = "none";
        window.location.href = "/safestop/front/";
    });

    confirmBtn.addEventListener("click", async () => {
        const password = inputPass.value.trim();

        // No aceptaremos contraseñas vacías
        if (password === "") {
            return;
        }

        try {
            const res = await fetch("/safestop/front/api/reset-data", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ password: password })
            });

            const json = await res.json();

            // Si la respuesta es exitosa, mostramos el mensaje de éxito
            // y redirigimos al index después de 2 segundos
            if (json.success) {
                errorMsg.style.display = "none";
                successMsg.style.display = "block";
                setTimeout(() => {
                    modal.style.display = "none";
                    window.location.href = "/safestop/front/";
                }, 2000);
            } else {
                errorMsg.textContent = json.error || "Error desconocido";
                errorMsg.style.display = "block";
            }

        } catch (e) {
            errorMsg.textContent = "Error en la conexión";
            errorMsg.style.display = "block";
        }
    });
});
