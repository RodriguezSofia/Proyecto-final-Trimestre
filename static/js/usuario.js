    // ======================================================================
// 1. CONTROL DEL MENÚ FLOTANTE DEL PERFIL
// ======================================================================

// Abre y cierra el recuadro flotante al hacer clic en el saludo o avatar superior
function toggleMenu() {
    const dropdown = document.getElementById('dropdownPerfil');
    if (dropdown) {
        dropdown.classList.toggle('oculto');
    }
}

// Muestra u oculta el formulario interno para cambiar nombre y correo
function toggleEditar() {
    const formEditar = document.getElementById('formEditar');
    if (formEditar) {
        formEditar.classList.toggle('oculto');
    }
}

// Cierra automáticamente el menú flotante si el usuario hace clic en cualquier otro lado de la pantalla
document.addEventListener('click', function (event) {
    const dropdown = document.getElementById('dropdownPerfil');
    const perfilDropdownBtn = document.querySelector('.perfil-dropdown');
    
    // Si el clic no fue dentro del menú ni en el botón que lo abre, lo esconde
    if (dropdown && perfilDropdownBtn && !dropdown.contains(event.target) && !perfilDropdownBtn.contains(event.target)) {
        dropdown.classList.add('oculto');
    }
});


// ======================================================================
// 2. GUARDAR CAMBIOS DEL PERFIL (FETCH API)
// ======================================================================
async function guardarDatosPerfil() {
    const nuevoNombre = document.getElementById('nuevoNombre').value.trim();
    const nuevoCorreo = document.getElementById('nuevoCorreo').value.trim();

    // Validación simple en el cliente
    if (!nuevoNombre || !nuevoCorreo) {
        Swal.fire({
            icon: 'error',
            title: 'Campos vacíos',
            text: 'Por favor, rellena todos los campos antes de guardar.'
        });
        return;
    }

    try {
        // Petición al servidor Flask para actualizar los datos
        const response = await fetch('/editar_perfil', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                nombre: nuevoNombre,
                correo: nuevoCorreo
            })
        });

        const result = await response.json();

        if (response.ok) {
            Swal.fire({
                icon: 'success',
                title: '¡Perfil actualizado!',
                text: result.mensaje || 'Tus datos se han guardado con éxito.',
                confirmButtonColor: '#147D7D'
            }).then(() => {
                location.reload(); // Recarga la página para refrescar el nombre en la barra superior
            });
        } else {
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: result.error || 'No se pudieron actualizar los datos.'
            });
        }
    } catch (error) {
        console.error("Error al actualizar el perfil:", error);
        Swal.fire({
            icon: 'error',
            title: 'Error de conexión',
            text: 'No se pudo comunicar con el servidor.'
        });
    }
}


// ======================================================================
// 3. MODAL DE ELIMINACIÓN DE CUENTA
// ======================================================================
function confirmarEliminarCuenta() {
    if (window.event) {
        window.event.preventDefault();
    }
    const modal = document.getElementById('modalEliminar');
    if (modal) {
        modal.classList.add('active');
    }
}

// Ocultar modal
function cerrarModalEliminar() {
    const modal = document.getElementById('modalEliminar');
    if (modal) {
        modal.classList.remove('active');
    }
}

// Ejecutar eliminación de cuenta
async function eliminarCuenta() {
    try {
        const response = await fetch('/eliminar_cuenta', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        // Si Flask redirecciona correctamente
        if (response.redirected) {
            cerrarModalEliminar();
            Swal.fire({
                icon: 'success',
                title: 'Cuenta eliminada',
                text: 'Tu cuenta ha sido desactivada correctamente.',
                confirmButtonColor: '#F54388'
            }).then(() => {
                window.location.href = response.url;
            });
        } else {
            Swal.fire({
                icon: 'error',
                title: 'No se pudo eliminar',
                text: 'Hubo un problema al procesar la solicitud.'
            });
        }
    } catch (error) {
        console.error("Error al eliminar la cuenta:", error);
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'No se pudo conectar con el servidor para eliminar la cuenta.'
        });
    }
}

// ======================================================================
// CERRAR MODAL AL HACER CLICK FUERA
// ======================================================================

window.addEventListener('click', function(e) {
    const modal = document.getElementById('modalEliminar');
    if (e.target === modal) {
        cerrarModalEliminar();
    }
});