<template>

  <div class="admin-echarts">

    <div id="echarts-main" style="width: 50%; height: 500px"  ></div>

  </div>

</template>

<script setup>

  import * as echarts from 'echarts';
  import { onMounted, onBeforeUnmount } from 'vue';
  import { useI18n } from 'vue-i18n';

  const { t } = useI18n();

  let myChart = null;

  function getRecentWeekDates() {
    const dates = [];
    const now = new Date();
    for (let i = 0; i < 7; i++) {
      const date = new Date(now);
      date.setDate(now.getDate() - (6 - i));
      dates.push(date);
    }
    return dates;
  }

  onMounted(() => {
    const chartDom = document.getElementById('echarts-main');
    myChart = echarts.init(chartDom);
    const recentWeekDates = getRecentWeekDates();

    const option = {
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow'
        }
      },

      legend: {

        data:[t('echarts.quantity')]

      },
      grid: {
        left: '3%',
        right: '4%',
        top:'10%',
        bottom: '5%',
        containLabel: true
      },
      xAxis: [
        {
          type: 'time',
          name: t('echarts.date'),
          nameLocation: 'middle',
          nameTextStyle: {
            color: '#333',
            fontSize: 14
          },
          nameGap:30,// 设置名称与 X 轴之间的距离
          splitLine: { show: false },
          axisLabel: {
            formatter: function (value) {
              const date = new Date(value);
              return date.toLocaleDateString();
            },

          }
        }
      ],
      yAxis: [
        {
          type: 'value',
          name: t('echarts.quantity'),
          nameLocation: 'end',
          nameTextStyle: {
            color: '#333',
            fontSize: 14
          },
        }
      ],
      series: [
        {
          name: 'Direct',
          type: 'bar', // 改为柱状图
          data: recentWeekDates.map((date, index) => [
            date.getTime(),
            [10, 52, 200, 334, 390, 330, 220][index]
          ])
        }
      ]
    };

    myChart.setOption(option);

  });

  onBeforeUnmount(() => {
    if (myChart) {
      echarts.dispose(myChart);
      myChart = null;
    }
  });

</script>



<style scoped>


</style>

