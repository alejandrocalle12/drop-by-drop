
document.addEventListener("DOMContentLoaded", function () {

    const prestamoSelect = document.getElementById("prestamo_id");
    const valorPagoInput = document.getElementById("valor_pago");

    if (!prestamoSelect || !valorPagoInput) {
        return;
    }

    const clienteInput = document.getElementById("cliente");
    const capitalInput = document.getElementById("capital");
    const saldoInput = document.getElementById("saldo");

    const saldoAnteriorOutput = document.getElementById("saldoAnterior");
    const abonoOutput = document.getElementById("abonoPreview");
    const nuevoSaldoOutput = document.getElementById("nuevoSaldo");

    const warning = document.getElementById("paymentWarning");
    const submitButton = document.getElementById("btnSavePayment");

    let saldoDisponible = 0;

    const formatoMoneda = new Intl.NumberFormat("es-CO", {
        style: "currency",
        currency: "COP",
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });

    function limpiarFormulario() {

        clienteInput.value = "";
        capitalInput.value = "";
        saldoInput.value = "";

        saldoDisponible = 0;

        saldoAnteriorOutput.textContent = formatoMoneda.format(0);
        abonoOutput.textContent = formatoMoneda.format(0);
        nuevoSaldoOutput.textContent = formatoMoneda.format(0);

        warning.textContent = "";
        warning.classList.remove("invalid");

        submitButton.disabled = true;
    }

    function seleccionarPrestamo() {

        const option = prestamoSelect.selectedOptions[0];

        if (!option || !option.value) {
            limpiarFormulario();
            return;
        }

        clienteInput.value = option.dataset.cliente;

        const capital = Number(option.dataset.capital);
        saldoDisponible = Number(option.dataset.saldo);

        capitalInput.value = formatoMoneda.format(capital);
        saldoInput.value = formatoMoneda.format(saldoDisponible);

        saldoAnteriorOutput.textContent =
            formatoMoneda.format(saldoDisponible);

        calcularNuevoSaldo();
    }

    function calcularNuevoSaldo() {

        const valorPago = Number(valorPagoInput.value);

        abonoOutput.textContent =
            formatoMoneda.format(
                Number.isFinite(valorPago) ? valorPago : 0
            );

        warning.textContent = "";
        warning.classList.remove("invalid");

        if (
            !Number.isFinite(valorPago) ||
            valorPago <= 0
        ) {
            nuevoSaldoOutput.textContent =
                formatoMoneda.format(saldoDisponible);

            warning.textContent =
                "Ingresa un valor de pago mayor que cero.";

            warning.classList.add("invalid");
            submitButton.disabled = true;
            return;
        }

        if (valorPago > saldoDisponible) {

            nuevoSaldoOutput.textContent =
                formatoMoneda.format(0);

            warning.textContent =
                "El abono no puede superar el saldo pendiente.";

            warning.classList.add("invalid");
            submitButton.disabled = true;
            return;
        }

        const nuevoSaldo = Math.round(
            (saldoDisponible - valorPago) * 100
        ) / 100;

        nuevoSaldoOutput.textContent =
            formatoMoneda.format(nuevoSaldo);

        submitButton.disabled = false;

        if (nuevoSaldo === 0) {
            warning.textContent =
                "Con este pago el préstamo quedará completamente cancelado.";
        }
    }

    prestamoSelect.addEventListener(
        "change",
        seleccionarPrestamo
    );

    valorPagoInput.addEventListener(
        "input",
        calcularNuevoSaldo
    );

    limpiarFormulario();

});
