
document.addEventListener("DOMContentLoaded", function () {

    const capitalInput = document.getElementById("capital");
    const interesInput = document.getElementById("porcentaje_interes");
    const cuotasInput = document.getElementById("numero_cuotas");
    const fechaPrestamoInput = document.getElementById("fecha_prestamo");

    const interesMensualOutput = document.getElementById("interesMensual");
    const interesAcumuladoOutput = document.getElementById("interesAcumulado");
    const pagoTotalOutput = document.getElementById("pagoTotal");
    const cuotaMensualOutput = document.getElementById("cuotaMensual");
    const cuotaRealOutput = document.getElementById("cuotaReal");
    const fechaVencimientoOutput = document.getElementById("fechaVencimiento");

    const formatoMoneda = new Intl.NumberFormat("es-CO", {
        style: "currency",
        currency: "COP",
        maximumFractionDigits: 2
    });

    function redondearMillar(valor) {
        return Math.floor(valor / 1000 + 0.5) * 1000;
    }

    function calcularFechaVencimiento(fecha, meses) {

        if (!fecha || !Number.isInteger(meses) || meses <= 0) {
            return null;
        }

        const partes = fecha.split("-").map(Number);

        const anio = partes[0];
        const mes = partes[1] - 1;
        const dia = partes[2];

        const fechaBase = new Date(anio, mes, 1);

        fechaBase.setMonth(fechaBase.getMonth() + meses);

        const ultimoDia = new Date(
            fechaBase.getFullYear(),
            fechaBase.getMonth() + 1,
            0
        ).getDate();

        const diaFinal = Math.min(dia, ultimoDia);

        const fechaFinal = new Date(
            fechaBase.getFullYear(),
            fechaBase.getMonth(),
            diaFinal
        );

        const anioFinal = fechaFinal.getFullYear();
        const mesFinal = String(fechaFinal.getMonth() + 1).padStart(2, "0");
        const diaFormateado = String(fechaFinal.getDate()).padStart(2, "0");

        return `${diaFormateado}/${mesFinal}/${anioFinal}`;
    }

    function calcularPrestamo() {

        const capital = Number(capitalInput.value);
        const porcentaje = Number(interesInput.value);
        const cuotas = Number(cuotasInput.value);

        if (
            !Number.isFinite(capital) ||
            !Number.isFinite(porcentaje) ||
            !Number.isInteger(cuotas) ||
            capital <= 0 ||
            porcentaje <= 0 ||
            porcentaje > 100 ||
            cuotas <= 0
        ) {

            interesMensualOutput.textContent = formatoMoneda.format(0);
            interesAcumuladoOutput.textContent = formatoMoneda.format(0);
            pagoTotalOutput.textContent = formatoMoneda.format(0);
            cuotaMensualOutput.textContent = formatoMoneda.format(0);
            cuotaRealOutput.textContent = formatoMoneda.format(0);

        } else {

            const tasa = porcentaje / 100;

            const interesMensual = capital * tasa;

            const interesAcumulado = interesMensual * cuotas;

            const pagoTotal = capital + interesAcumulado;

            const cuotaMensual = pagoTotal / cuotas;

            const cuotaReal = redondearMillar(cuotaMensual);

            interesMensualOutput.textContent =
                formatoMoneda.format(interesMensual);

            interesAcumuladoOutput.textContent =
                formatoMoneda.format(interesAcumulado);

            pagoTotalOutput.textContent =
                formatoMoneda.format(pagoTotal);

            cuotaMensualOutput.textContent =
                formatoMoneda.format(cuotaMensual);

            cuotaRealOutput.textContent =
                formatoMoneda.format(cuotaReal);
        }

        // Calcular y mostrar fecha de vencimiento
        if (fechaVencimientoOutput) {

            const fechaVencimiento = calcularFechaVencimiento(
                fechaPrestamoInput.value,
                cuotas
            );

            fechaVencimientoOutput.textContent =
                fechaVencimiento || "Pendiente de cálculo";
        }
    }

    capitalInput.addEventListener("input", calcularPrestamo);
    interesInput.addEventListener("input", calcularPrestamo);
    cuotasInput.addEventListener("input", calcularPrestamo);
    fechaPrestamoInput.addEventListener("change", calcularPrestamo);

    calcularPrestamo();

});
