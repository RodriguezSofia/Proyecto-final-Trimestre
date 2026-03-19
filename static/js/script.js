// ELEMENTOS
const nombreInput = document.getElementById("nombre");
const correoInput = document.getElementById("correo");
const nombreTexto = document.getElementById("nombreTexto");
const correoTexto = document.getElementById("correoTexto");
const fotoPerfil = document.getElementById("fotoPerfil");
const inputFoto = document.getElementById("inputFoto");

// GUARDAR DATOS
function guardarDatos() {
    const nombre = nombreInput.value;
    const correo = correoInput.value;

    localStorage.setItem("nombre", nombre);
    localStorage.setItem("correo", correo);

    nombreTexto.textContent = nombre;
    correoTexto.textContent = correo;

    alert("Datos guardados");
}

// CARGAR DATOS
window.onload = function () {
    const nombre = localStorage.getItem("nombre");
    const correo = localStorage.getItem("correo");
    const foto = localStorage.getItem("foto");

    if (nombre) {
        nombreTexto.textContent = nombre;
        nombreInput.value = nombre;
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

// BOTONES
function misCompras() {
    alert("Aquí irían las compras 🛒");
}

function cerrarSesion() {
    alert("Sesión cerrada 🔒");
}

function eliminarCuenta() {
    if (confirm("¿Seguro que quieres eliminar tu cuenta?")) {
        localStorage.clear();
        location.reload();
    }
}