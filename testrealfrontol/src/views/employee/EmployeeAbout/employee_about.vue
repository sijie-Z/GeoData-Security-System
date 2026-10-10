<template>
  <div class="employee-about-page page-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>{{ $t('empAbout.aboutSystem') }}</span>
        </div>
      </template>
      <div class="about-content">
        <h1>{{ $t('empAbout.systemName') }}</h1>
        <p><strong>{{ $t('empAbout.version') }}</strong> v1.0</p>
        <p><strong>{{ $t('empAbout.releaseDate') }}</strong> 2025</p>

        <el-divider />

        <h2>{{ $t('empAbout.systemIntro') }}</h2>
        <p>{{ $t('empAbout.systemDescription') }}</p>

        <h2>{{ $t('empAbout.mainFeatures') }}</h2>
        <ul>
          <li><strong>{{ $t('empAbout.featureDataCatalog') }}</strong> {{ $t('empAbout.featureDataCatalogDesc') }}</li>
          <li><strong>{{ $t('empAbout.featureDataApplication') }}</strong> {{ $t('empAbout.featureDataApplicationDesc') }}</li>
          <li><strong>{{ $t('empAbout.featureWatermark') }}</strong> {{ $t('empAbout.featureWatermarkDesc') }}</li>
          <li><strong>{{ $t('empAbout.featureDownload') }}</strong> {{ $t('empAbout.featureDownloadDesc') }}</li>
          <li><strong>{{ $t('empAbout.featureNotification') }}</strong> {{ $t('empAbout.featureNotificationDesc') }}</li>
          <li><strong>{{ $t('empAbout.featureLog') }}</strong> {{ $t('empAbout.featureLogDesc') }}</li>
          <li><strong>{{ $t('empAbout.featureProfile') }}</strong> {{ $t('empAbout.featureProfileDesc') }}</li>
        </ul>

        <h2>{{ $t('empAbout.techDescription') }}</h2>
        <p>{{ $t('empAbout.techDetails') }}</p>

        <el-divider />

        <p>{{ $t('empAbout.footer') }}</p>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n';
import { ElDivider } from 'element-plus';

const { t } = useI18n();
</script>

<style scoped>
.employee-about-page {
  padding: 24px;
  background-color: var(--bg-canvas);
  min-height: calc(100vh - 60px - 40px);
  display: flex;
  justify-content: center;
  align-items: flex-start;
}

.box-card {
  width: 100%;
  max-width: 800px;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0,0,0,.04);
}

.card-header {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-1);
}

.about-content {
  padding: 20px;
  line-height: 1.8;
  color: var(--text-2);
}

.about-content h1 {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-1);
  margin-top: 15px;
  margin-bottom: 20px;
}

.about-content h2 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-1);
  margin-top: 25px;
  margin-bottom: 15px;
  border-bottom: 1px solid var(--border-subtle);
  padding-bottom: 5px;
}

.about-content p {
  margin-bottom: 10px;
}

.about-content ul {
  list-style-type: disc;
  margin-left: 20px;
  margin-bottom: 10px;
}

.about-content li {
  margin-bottom: 5px;
}
</style>
