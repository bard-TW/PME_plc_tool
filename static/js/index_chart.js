const ctx = document.getElementById('myChart');

var chart_dates = []
var chart_datasets = []

var myLineChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [],
        datasets: []
    }
});


function reset_chart() {
    var chart = Chart.getChart(ctx);
    if (chart) {
        chart.destroy();
    }

    // if (history_columns_list.length === 0){
    //     alert('請先紀錄logs')
    //     return
    // }

    history_data = history_table.rows().data().toArray()

    if (history_data.length === 0) {
        alert('請先紀錄logs')
        return
    }

    chart_datasets = []
    for ([key, value] of Object.entries(history_islog_dict)) {
        chart_datasets.push({ label: `${value} #${key}`, id: key, data: [] })
    }

    chart_dates = []

    for ([i, value] of history_data.slice(0,60).reverse().entries()) {

        // chart_dates.push(new Date(value.date_time.replace(' ', 'T')))
        chart_dates.push(value.date_time.split(" ")[1])
        for ([_, chart_value] of chart_datasets.entries()) {
            if (chart_value.id in value) {
                chart_value.data.push(value[chart_value.id])
            } else {
                chart_value.data.push('')
            }
        }
    }

    myLineChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chart_dates,
            datasets: chart_datasets
        },
        options: {
            scales: {
                x: {
                    ticks:{
                        maxTicksLimit: 10
                    }
                }
            }
        }
    });
}

function update_chart(data) {
    var myLineChart = Chart.getChart(ctx);
    if (myLineChart) {
        chart_dates.push(data.date_time.split(" ")[1])
        // chart_dates.push(new Date(data.date_time.replace(' ', 'T')))
        for ([_, chart_value] of chart_datasets.entries()) {
            if (chart_value.id in data) {
                chart_value.data.push(data[chart_value.id])
            } else {
                chart_value.data.push('')
            }
            if (chart_value.data.length > 60){
                chart_value.data.shift()
            }
        }

        if (chart_dates.length > 60){
            chart_dates.shift()
        }
        myLineChart.update()
    }
}


// myLineChart.destroy()
// myLineChart.update()