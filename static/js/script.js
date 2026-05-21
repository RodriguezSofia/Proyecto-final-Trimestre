// ELEMENTOS
const nombreInput = document.getElementById("nombre");
const correoInput = document.getElementById("correo");
const nombreTexto = document.getElementById("nombreTexto");
const correoTexto = document.getElementById("correoTexto");
const fotoPerfil = document.getElementById("fotoPerfil");
const inputFoto = document.getElementById("inputFoto");

// --- FUNCIÓN GUARDAR ---
function guardarDatos() {
    const nombre = nombreInput.value;
    const correo = correoInput.value;

    if (nombre === "" || correo === "") {
        alert("Por favor, llena los campos");
        return;
    }

    //Guarda en la memoria local
    localStorage.setItem("nombre", nombre);
    localStorage.setItem("correo", correo);

    //Actualiza la TARJETA
    nombreTexto.textContent = nombre;
    correoTexto.textContent = correo;

    //Actualiza el SALUDO de arriba (Busca el ID saludoTop)
    const saludoTop = document.getElementById("saludoTop");
    if (saludoTop) {
        saludoTop.textContent = nombre;
    }

    alert("¡Nombre actualizado en Annia Ice Cream!");
}

// --- CARGAR DATOS AL INICIAR ---
window.onload = function () {
    const nombre = localStorage.getItem("nombre");
    const correo = localStorage.getItem("correo");
    const foto = localStorage.getItem("foto");

    if (nombre) {
        nombreTexto.textContent = nombre;
        nombreInput.value = nombre;
        // También carga el saludo de arriba al refrescar
        const saludoTop = document.getElementById("saludoTop");
        if (saludoTop) saludoTop.textContent = nombre;
    }

    if (correo) {
        correoTexto.textContent = correo;
        correoInput.value = correo;
    }

    if (foto) {
        fotoPerfil.src = foto;
    }
};

// FOTO
inputFoto.addEventListener("change", function () {
    const file = this.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function (e) {
            fotoPerfil.src = e.target.result;
            localStorage.setItem("foto", e.target.result);
        };
        reader.readAsDataURL(file);
    }
});
// Variable de sesión
const usuarioLogueado = "{{ 'true' if session.get('usuario_nombre') else 'false' }}" === "true"

function toggleMenu() {
    const menu = document.getElementById("dropdownPerfil");
    if (menu) {
        menu.classList.toggle("oculto");
    }
}

function toggleEditar() {
    document.getElementById("formEditar").classList.toggle("oculto");
}

// GUARDAR DATOS (Nombre y Correo)
function guardarDatosPerfil() {
    const nombre = document.getElementById("nuevoNombre").value;
    const correo = document.getElementById("nuevoCorreo").value;

    fetch('/actualizar_perfil', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nombre: nombre, correo: correo })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById("nombreTexto").textContent = nombre;
            document.getElementById("correoTexto").textContent = correo;
            
            const saludoTop = document.getElementById("saludoTop");
            if (saludoTop) {
                saludoTop.textContent = "Hola, " + nombre;
            }
            
            Swal.fire({
                title: "¡Guardado!",
                text: "Datos actualizados correctamente",
                icon: "success",
                confirmButtonColor: "#ff9ecf"
            });
            toggleEditar();
        }
    });
}

// ELIMINAR CUENTA
function eliminarCuenta() {
    Swal.fire({
        title: "¿Estás seguro?",
        text: "Esta acción eliminará tu cuenta de forma permanente.",
        icon: "warning",
        showCancelButton: true,
        confirmButtonColor: "#ff4d6d",
        cancelButtonColor: "#aaa",
        confirmButtonText: "Sí, eliminar",
        cancelButtonText: "Cancelar"
    }).then((result) => {
        if (result.isConfirmed) {
            fetch('/eliminar_cuenta', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    Swal.fire("Eliminada", "Tu cuenta ha sido borrada.", "success")
                    .then(() => { window.location.href = "/"; });
                }
            });
        }
    });
}

// ACTUALIZAR FOTO
const inputFoto = document.getElementById("inputFoto");
if (inputFoto) {
    inputFoto.addEventListener("change", function () {
        const file = this.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function (e) {
                const base64Image = e.target.result;
                fetch('/actualizar_foto', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ foto_url: base64Image })
                })
                .then(res => res.json())
                .then(data => {
                    if(data.success) {
                        document.querySelector(".header-perfil img").src = base64Image;
                        document.querySelector(".avatar-nav").src = base64Image; 
                    }
                });
            };
            reader.readAsDataURL(file);
        }
    });
}

// CERRAR AL CLICKEAR FUERA
window.addEventListener('click', function(e) {
    const menu = document.getElementById("dropdownPerfil");
    const trigger = document.querySelector('.perfil-dropdown');
    if (menu && trigger && !trigger.contains(e.target) && !menu.contains(e.target)) {
        menu.classList.add('oculto');
    }
});