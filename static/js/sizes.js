try {

    const response = await fetch("/api/sizes");

    if (!response.ok) {
        throw new Error("HTTP " + response.status);
    }

    const sizes = await response.json();

    sizes.sort(compareSizes);

    const tableBody =
        document.getElementById("sizes-table");

    tableBody.innerHTML = "";

    for (const size of sizes) {

        const row =
            document.createElement("tr");


        /*
         * REPEAT COUNTER HIGHLIGHT
         */

        if (size.continuous_counter > REPEAT_COUNTER) {
            row.classList.add("repeat-highlight");
        }


        /*
         * DIRECTION
         */

        const directionSymbol =
            size.direction === "up"
                ? "↗"
                : "↘";


        /*
         * BREAKTHROUGH STATUS
         */

        const breakthrough =
            getBreakthroughStatus(size);


        /*
         * ROW CONTENT
         */

        row.innerHTML = `

            <td>
                ${formatDate(size.signal_date)}
            </td>

            <td>
                ${escapeHtml(size.coin)}
            </td>

            <td>
                ${formatNumber(size.size_price)}
            </td>

            <td>
                ${formatNumber(size.extremum_price)}
            </td>

            <td>
                ${formatNumber(size.current_price)}
            </td>

            <td>
                ${directionSymbol}
                ${formatNumber(size.distance)}%
            </td>

            <td>
                x${formatNumber(size.size_vs_max_neighbor, 1)}
            </td>

            <td>
                x${formatNumber(size.size_vs_avg_volume, 1)}
            </td>

            <td>
                ${formatTime(size.first_seen)}
            </td>

            <td>
                ${formatTime(size.last_seen)}
            </td>

            <td>
                ${size.continuous_counter}
                (${size.total_counter})
            </td>

            <td class="${breakthrough.className}">
                ${breakthrough.text}
            </td>

        `;

        tableBody.appendChild(row);
    }

} catch (error) {

    console.error(
        "Failed to update table:",
        error
    );

}
