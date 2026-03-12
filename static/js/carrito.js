const usuarioLogueado = "{{ 'true' if session.get('usuario_nombre') else 'false' }}" === "true";
let carrito = [];

// Elementos DOM
const carritoCount = document.getElementById("carritoCount");
const carritoCountFloat = document.getElementById("carritoCountFloat");
const listaCarrito = document.getElementById("listaCarrito");

// ─────────── AGREGAR PRODUCTO ───────────
function agregarAlCarrito(idProducto, nombre, precio, numeroBolas) {
    let sabores = [];
    let topping = null;

    // Leer cada sabor según numeroBolas
    for (let i = 1; i <= numeroBolas; i++) {
        const select = document.getElementById(`sabor-${idProducto}-${i}`);
        const idSabor = Number(select.value); // Para enviar al backend
        const nombreSabor = select.options[select.selectedIndex].text; // Para mostrar en pantalla
        sabores.push({ id: idSabor, nombre: nombreSabor });
    }
    // Leer topping (si existe)
const selectTopping = document.getElementById(`topping-${idProducto}`);
if (selectTopping && selectTopping.value !== "") {
    topping = {
        id: Number(selectTopping.value),
        nombre: selectTopping.options[selectTopping.selectedIndex].text
    };
}


    carrito.push({
        id_producto: Number(idProducto),
        nombre,
        precio: Number(precio.toString().replace(/\./g, "")),
        sabores,
        topping 
    });

    actualizarContadores();
    renderCarrito();
}

// ─────────── ELIMINAR PRODUCTO ───────────
function eliminarProducto(index) {
    carrito.splice(index, 1);
    actualizarContadores();
    renderCarrito();
}

// ─────────── ACTUALIZAR CONTADORES ───────────
function actualizarContadores() {
    if (carritoCount) carritoCount.textContent = carrito.length;
    if (carritoCountFloat) carritoCountFloat.textContent = carrito.length;
}

// ─────────── RENDER CARRITO ───────────
function renderCarrito() {
    if (!listaCarrito) return;

    if (carrito.length === 0) {
        listaCarrito.innerHTML = "<p>Tu carrito está vacío </p>";
        return;
    }

    let total = 0;

    listaCarrito.innerHTML = carrito.map((item, index) => {
        const precioFormateado = parseInt(item.precio).toLocaleString('es-CO', { minimumFractionDigits: 0 });
        total += item.precio;

        // Mostrar nombres de sabores
        const saboresHTML = item.sabores.map(s => `<br>${s.nombre}`).join("");
        const toppingHTML = item.topping 
    ? `<br><small>Topping: ${item.topping.nombre}</small>`
    : "";


        return `
        <div class="d-flex justify-content-between align-items-center border-bottom py-2">
            <div>
                <strong>${item.nombre}</strong> — $${precioFormateado}
                ${saboresHTML}
                ${toppingHTML}
            </div>
            <button class="btn btn-danger btn-sm" onclick="eliminarProducto(${index})">
                <i class="bi bi-trash3-fill"></i>
            </button>
        </div>`;
    }).join("");

    // Inputs ocultos para enviar al backend
    const carritoContainer = document.getElementById("carritoContainer");
    carritoContainer.innerHTML = "";
    carrito.forEach((item, index) => {
        const div = document.createElement("div");
        div.classList.add("mb-2");

        div.innerHTML += `<input type="hidden" name="carrito[${index}][id_producto]" value="${item.id_producto}">`;
        item.sabores.forEach((sabor, i) => {
            div.innerHTML += `<input type="hidden" name="carrito[${index}][sabores][${i}]" value="${sabor.id}">`;
        });
        if (item.topping) {
            div.innerHTML += `<input type="hidden" name="carrito[${index}][topping]" value="${item.topping.id}">`;
        }
        div.innerHTML += `<input type="hidden" name="carrito[${index}][precio]" value="${item.precio}">`;

        carritoContainer.appendChild(div);
    });

    // Mostrar total
    const totalDiv = document.createElement("div");
    totalDiv.classList.add("mt-3", "fw-bold", "text-end");
    totalDiv.innerHTML = `Total: $${total.toLocaleString('es-CO', { minimumFractionDigits: 0 })}`;
    carritoContainer.appendChild(totalDiv);
}

// ─────────── VALIDAR SESIÓN ANTES DE COMPRAR ───────────
function validarCompra() {
    if (!usuarioLogueado) {
        const loginModal = new bootstrap.Modal(document.getElementById("modalLogin"));
        loginModal.show();
        return;
    }
    comprar();
}

// ─────────── COMPRAR ───────────
function comprar() {
    if (carrito.length === 0) {
        alert("Tu carrito está vacío");
        return;
    }

    // Guardar carrito en localStorage (para mostrar en confirmar pedido)
    localStorage.setItem("carrito", JSON.stringify(carrito));

    // Guardar total
    const total = carrito.reduce((suma, p) => suma + p.precio, 0);
    localStorage.setItem("total", total);

    // Guardar usuario
    localStorage.setItem("usuario", "{{ session.get('usuario_nombre') }}");

    // Redirigir a confirmar pedido
    window.location.href = "/confirmar_pedido";
}

// ─────────── CARGAR CARRITO AL INICIAR PÁGINA ───────────
document.addEventListener("DOMContentLoaded", () => {
    const carritoGuardado = JSON.parse(localStorage.getItem("carrito"));
    if (carritoGuardado && carritoGuardado.length > 0) {
        carrito = carritoGuardado;
        actualizarContadores();
        renderCarrito();
    }
});