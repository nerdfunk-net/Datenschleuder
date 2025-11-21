<template>
  <div>
    <PageTitle
      :heading="heading"
      :subheading="subheading"
      :icon="icon"
    />
    <div class="content">
      <div class="row">
        <div class="col-md-6">
          <div class="main-card mb-3 card">
            <div class="card-header">
              <h5 class="card-title mb-0">
                Doughnut Chart
              </h5>
            </div>
            <div class="card-body">
              <div class="chart-container">
                <doughnut />
              </div>
            </div>
          </div>
          <div class="main-card mb-3 card">
            <div class="card-header">
              <h5 class="card-title mb-0">
                Radar Chart
              </h5>
            </div>
            <div class="card-body">
              <div class="chart-container">
                <radar />
              </div>
            </div>
          </div>
        </div>
        <div class="col-md-6">
          <div class="main-card mb-3 card">
            <div class="card-header">
              <h5 class="card-title mb-0">
                Polar Area Chart
              </h5>
            </div>
            <div class="card-body">
              <div class="chart-container">
                <polar />
              </div>
            </div>
          </div>
          <div class="main-card mb-3 card">
            <div class="card-header">
              <h5 class="card-title mb-0">
                Pie Chart
              </h5>
            </div>
            <div class="card-body">
              <div class="chart-container">
                <pie />
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="row">
        <div class="col-md-6">
          <div class="main-card mb-3 card">
            <div class="card-header">
              <h5 class="card-title mb-0">
                Line Chart
              </h5>
            </div>
            <div class="card-body">
              <div class="chart-container">
                <lineeg />
              </div>
            </div>
          </div>
          <div class="main-card mb-3 card">
            <div class="card-header">
              <h5 class="card-title mb-0">
                Area Chart
              </h5>
            </div>
            <div class="card-body">
              <div class="chart-container">
                <areaeg />
              </div>
            </div>
          </div>
        </div>
        <div class="col-md-6">
          <div class="main-card mb-3 card">
            <div class="card-header">
              <h5 class="card-title mb-0">
                Vertical Bar Chart
              </h5>
            </div>
            <div class="card-body">
              <div class="chart-container">
                <bar />
              </div>
            </div>
          </div>
          <div class="main-card mb-3 card">
            <div class="card-header">
              <h5 class="card-title mb-0">
                Horizontal Bar Chart
              </h5>
            </div>
            <div class="card-body">
              <div class="chart-container">
                <barhoriz />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import PageTitle from "../../Layout/Components/PageTitle.vue";

import doughnut from "./Chartjs/DoughnutSimple.vue";
import radar from "./Chartjs/RadarSimple.vue";
import polar from "./Chartjs/PolarSimple.vue";
import pie from "./Chartjs/PieSimple.vue";
import lineeg from "./Chartjs/LineSimple.vue";
import areaeg from "./Chartjs/AreaSimple.vue";
import bar from "./Chartjs/BarSimple.vue";
import barhoriz from "./Chartjs/BarHorizontalSimple.vue";

export default {
  components: {
    PageTitle,

    doughnut,
    radar,
    polar,
    pie,
    lineeg,
    areaeg,
    bar,
    barhoriz,
  },
  data: () => ({
    heading: "ChartJS",
    subheading: "Huge selection of charts created with the Vue ChartJS Plugin",
    icon: "pe-7s-bandaid icon-gradient bg-amy-crisp",
  }),
};
</script>

<style scoped>
.chart-container {
  position: relative;
  height: 300px;
  width: 100%;
}

.main-card {
  transition: all 0.3s ease;
  border: 1px solid rgba(0, 0, 0, 0.125);
}

.main-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
}

.card-header {
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border-bottom: 1px solid #dee2e6;
  font-weight: 600;
}

.card-title {
  color: #212529;
  font-weight: 600;
}

/* Responsive chart containers */
@media (max-width: 768px) {
  .chart-container {
    height: 250px;
  }
}

@media (max-width: 576px) {
  .chart-container {
    height: 200px;
  }
}

/* Enhanced card styling */
.card {
  border-radius: 0.5rem;
  overflow: hidden;
}

.card-body {
  padding: 1.5rem;
}

.card-header {
  padding: 1rem 1.5rem;
  border-radius: 0.5rem 0.5rem 0 0;
}

/* Chart loading state */
.chart-container canvas {
  border-radius: 0.25rem;
}

/* Ensure charts are responsive */
.chart-container > div {
  position: relative !important;
  height: 100% !important;
}
</style>
