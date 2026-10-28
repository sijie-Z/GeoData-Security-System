<template>
  <div class="employee-help-page page-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>{{ $t('empHelp.systemHelp') }}</span>
        </div>
      </template>
      <div class="help-content">
        <h1>{{ $t('empHelp.welcome') }}</h1>
        <p>{{ $t('empHelp.intro') }}</p>

        <h2>{{ $t('empHelp.dataCatalog') }}</h2>
        <p>{{ $t('empHelp.dataCatalogDesc') }}</p>
        <p>{{ $t('empHelp.dataCatalogDetail') }}</p>

        <h2>{{ $t('empHelp.myApplications') }}</h2>
        <p>{{ $t('empHelp.myApplicationsDesc') }}</p>

        <h2>{{ $t('empHelp.myDownloads') }}</h2>
        <p>{{ $t('empHelp.myDownloadsDesc') }}</p>

        <h2>{{ $t('empHelp.operationHistory') }}</h2>
        <p>{{ $t('empHelp.operationHistoryDesc') }}</p>

        <h2>{{ $t('empHelp.myNotifications') }}</h2>
        <p>{{ $t('empHelp.myNotificationsDesc') }}</p>

        <h2>{{ $t('empHelp.personalCenter') }}</h2>
        <p>{{ $t('empHelp.personalCenterDesc') }}</p>

        <h2>{{ $t('empHelp.aboutSystem') }}</h2>
        <p>{{ $t('empHelp.aboutSystemDesc') }}</p>

        <el-divider />

        <p>{{ $t('empHelp.footer') }}</p>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ElDivider } from 'element-plus';
</script>

<style scoped>
.employee-help-page {
  padding: 24px;
  background-color: var(--bg-canvas);
  min-height: calc(100vh - 60px - 40px);
  display: flex;
  justify-content: center;
  align-items: flex-start;
}

.box-card {
  width: 100%;
  max-width: 900px;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0,0,0,.04);
}

.card-header {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-1);
}

.help-content {
  padding: 20px;
  line-height: 1.8;
  color: var(--text-2);
}

.help-content h1, .help-content h2 {
  color: var(--text-1);
  margin-top: 25px;
  margin-bottom: 15px;
}

.help-content h1 {
  font-size: 24px;
  font-weight: 700;
}

.help-content h2 {
  font-size: 18px;
  font-weight: 600;
  border-bottom: 1px solid var(--border-subtle);
  padding-bottom: 5px;
  margin-bottom: 15px;
}

.help-content p {
  margin-bottom: 10px;
}

.help-content ul {
  list-style-type: disc;
  margin-left: 20px;
  margin-bottom: 10px;
}

.help-content li {
  margin-bottom: 5px;
}
</style>
