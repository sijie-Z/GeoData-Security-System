<template>
  <div class="employee-help-page page-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>{{ $t('empHelp.systemHelp') }}</span>
        </div>
      </template>
      <div class="help-content">
        <h2>{{ $t('empHelp.welcome') }}</h2>
        <p>{{ $t('empHelp.intro') }}</p>

        <h3>{{ $t('empHelp.dataCatalog') }}</h3>
        <p>{{ $t('empHelp.dataCatalogDesc') }}</p>
        <p>{{ $t('empHelp.dataCatalogDetail') }}</p>

        <h3>{{ $t('empHelp.myApplications') }}</h3>
        <p>{{ $t('empHelp.myApplicationsDesc') }}</p>

        <h3>{{ $t('empHelp.myDownloads') }}</h3>
        <p>{{ $t('empHelp.myDownloadsDesc') }}</p>

        <h3>{{ $t('empHelp.operationHistory') }}</h3>
        <p>{{ $t('empHelp.operationHistoryDesc') }}</p>

        <h3>{{ $t('empHelp.myNotifications') }}</h3>
        <p>{{ $t('empHelp.myNotificationsDesc') }}</p>

        <h3>{{ $t('empHelp.personalCenter') }}</h3>
        <p>{{ $t('empHelp.personalCenterDesc') }}</p>

        <h3>{{ $t('empHelp.aboutSystem') }}</h3>
        <p>{{ $t('empHelp.aboutSystemDesc') }}</p>

        <el-divider />

        <p>{{ $t('empHelp.footer') }}</p>
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
.employee-help-page {
  padding: 24px;
  background-color: #f7f8fa;
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
  color: #333;
}

.help-content {
  padding: 20px;
  line-height: 1.8;
  color: #4b5563;
}

.help-content h2, .help-content h3 {
  color: #1d2129;
  margin-top: 25px;
  margin-bottom: 15px;
}

.help-content h2 {
  font-size: 24px;
  font-weight: 700;
}

.help-content h3 {
  font-size: 18px;
  font-weight: 600;
  border-bottom: 1px solid #eee;
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
