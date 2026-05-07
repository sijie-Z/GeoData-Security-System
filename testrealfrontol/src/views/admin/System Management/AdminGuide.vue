<template>
  <div class="guide-page">
    <el-card class="guide-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <h2>{{ $t('adminGuide.title') }}</h2>
          <el-tag type="success">{{ $t('adminGuide.beginner') }}</el-tag>
        </div>
      </template>

      <el-collapse v-model="activeSection">
        <!-- 系统概述 -->
        <el-collapse-item :title="$t('adminGuide.overview')" name="overview">
          <div class="section-content">
            <p>{{ $t('adminGuide.overviewDescPrefix') }}<strong>{{ $t('adminGuide.overviewDescBold') }}</strong>{{ $t('adminGuide.overviewDescSuffix') }}</p>
            <el-alert type="info" :closable="false" style="margin-top: 12px">
              <template #title>
                {{ $t('adminGuide.currentIdentityPrefix') }}<strong>{{ adminRoleName }}</strong>{{ $t('adminGuide.currentIdentitySuffix') }}
              </template>
            </el-alert>
          </div>
        </el-collapse-item>

        <!-- 管理员角色 -->
        <el-collapse-item :title="$t('adminGuide.roles')" name="roles">
          <div class="section-content">
            <el-table :data="roleData" border style="margin-top: 12px">
              <el-table-column prop="role" :label="$t('adminGuide.role')" width="100" />
              <el-table-column prop="permission" :label="$t('adminGuide.mainDuties')" />
              <el-table-column prop="watermark" :label="$t('adminGuide.watermarkPermission')" width="150" />
            </el-table>
          </div>
        </el-collapse-item>

        <!-- 审批流程 -->
        <el-collapse-item :title="$t('adminGuide.approvalProcess')" name="approval">
          <div class="section-content">
            <div class="flow-diagram">
              <div class="flow-item">
                <div class="flow-box">{{ $t('adminGuide.employeeSubmit') }}</div>
                <el-icon><ArrowRight /></el-icon>
              </div>
              <div class="flow-item">
                <div class="flow-box primary">{{ $t('adminGuide.admin1Review') }}</div>
                <el-icon><ArrowRight /></el-icon>
              </div>
              <div class="flow-item">
                <div class="flow-box success">{{ $t('adminGuide.admin2Review') }}</div>
                <el-icon><ArrowRight /></el-icon>
              </div>
              <div class="flow-item">
                <div class="flow-box warning">{{ $t('adminGuide.watermarkProcess') }}</div>
                <el-icon><ArrowRight /></el-icon>
              </div>
              <div class="flow-item">
                <div class="flow-box info">{{ $t('adminGuide.dataDistribution') }}</div>
              </div>
            </div>
            <el-divider />
            <h4>{{ $t('adminGuide.approvalSteps') }}</h4>
            <ol>
              <li>{{ $t('adminGuide.step1') }}</li>
              <li>{{ $t('adminGuide.step2') }}</li>
              <li>{{ $t('adminGuide.step3') }}</li>
              <li>{{ $t('adminGuide.step4') }}</li>
            </ol>
          </div>
        </el-collapse-item>

        <!-- 水印流程 -->
        <el-collapse-item :title="$t('adminGuide.watermarkFlow')" name="watermark">
          <div class="section-content">
            <el-steps :active="3" finish-status="success" simple style="margin-bottom: 20px">
              <el-step :title="$t('adminGuide.generate')" :description="$t('adminGuide.admin1')" />
              <el-step :title="$t('adminGuide.embed')" :description="$t('adminGuide.admin2')" />
              <el-step :title="$t('adminGuide.extract')" :description="$t('adminGuide.admin3')" />
            </el-steps>
            <el-alert type="warning" :closable="false">
              {{ $t('adminGuide.watermarkNote') }}
            </el-alert>
          </div>
        </el-collapse-item>

        <!-- 数据回收 -->
        <el-collapse-item :title="$t('adminGuide.dataRecall')" name="recall">
          <div class="section-content">
            <p>{{ $t('adminGuide.recallDesc') }}</p>
            <ol>
              <li>{{ $t('adminGuide.recallStep1') }}</li>
              <li>{{ $t('adminGuide.recallStep2') }}</li>
              <li>{{ $t('adminGuide.recallStep3') }}</li>
              <li>{{ $t('adminGuide.recallStep4') }}</li>
            </ol>
          </div>
        </el-collapse-item>

        <!-- 在线沟通 -->
        <el-collapse-item :title="$t('adminGuide.onlineChat')" name="chat">
          <div class="section-content">
            <p>{{ $t('adminGuide.chatDesc') }}</p>
            <el-button type="primary" @click="goToChat">{{ $t('adminGuide.enterChat') }}</el-button>
            <el-divider direction="vertical" />
            <span class="hint">{{ $t('adminGuide.chatHint') }}</span>
          </div>
        </el-collapse-item>

        <!-- 常见问题 -->
        <el-collapse-item :title="$t('adminGuide.faq')" name="faq">
          <div class="section-content">
            <el-collapse>
              <el-collapse-item :title="$t('adminGuide.faq1Q')" name="q1">
                <p>{{ $t('adminGuide.faq1A') }}</p>
              </el-collapse-item>
              <el-collapse-item :title="$t('adminGuide.faq2Q')" name="q2">
                <p>{{ $t('adminGuide.faq2A') }}</p>
              </el-collapse-item>
              <el-collapse-item :title="$t('adminGuide.faq3Q')" name="q3">
                <p>{{ $t('adminGuide.faq3A') }}</p>
              </el-collapse-item>
              <el-collapse-item :title="$t('adminGuide.faq4Q')" name="q4">
                <p>{{ $t('adminGuide.faq4A') }}</p>
              </el-collapse-item>
            </el-collapse>
          </div>
        </el-collapse-item>
      </el-collapse>
    </el-card>

    <!-- 快捷入口 -->
    <el-card class="shortcuts-card" shadow="hover" style="margin-top: 16px">
      <template #header>
        <span>{{ $t('adminGuide.shortcuts') }}</span>
      </template>
      <div class="shortcuts">
        <el-button type="primary" @click="goTo('/admin/approve_application/not_approved')">{{ $t('adminGuide.pendingApproval') }}</el-button>
        <el-button type="success" @click="goTo('/admin/employee_management/information_list')">{{ $t('adminGuide.employeeList') }}</el-button>
        <el-button type="warning" @click="goTo('/admin/system/chat')">{{ $t('adminGuide.onlineChatBtn') }}</el-button>
        <el-button type="info" @click="goTo('/admin/logs')">{{ $t('adminGuide.operationLog') }}</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/userStore'
import { ArrowRight } from '@element-plus/icons-vue'

const { t } = useI18n()
const router = useRouter()
const userStore = useUserStore()

const activeSection = ref(['overview'])

const adminRoleName = computed(() => {
  const num = (userStore.userNumber || '').toLowerCase()
  if (num.includes('admin1') || num.includes('adm1') || num === '22200214135') return t('adminGuide.admin1Role')
  if (num.includes('admin2') || num.includes('adm2') || num === '33300214135') return t('adminGuide.admin2Role')
  if (num.includes('admin3') || num.includes('adm3') || num === '44400214135') return t('adminGuide.admin3Role')
  return t('adminGuide.adminDefault')
})

const roleData = computed(() => [
  { role: t('adminGuide.role1'), permission: t('adminGuide.role1Duty'), watermark: t('adminGuide.watermarkGenerate') },
  { role: t('adminGuide.role2'), permission: t('adminGuide.role2Duty'), watermark: t('adminGuide.watermarkEmbed') },
  { role: t('adminGuide.role3'), permission: t('adminGuide.role3Duty'), watermark: t('adminGuide.watermarkExtract') },
])

const goTo = (path) => router.push(path)
const goToChat = () => router.push('/admin/system/chat')
</script>

<style scoped>
.guide-page {
  padding: 20px;
  max-width: 900px;
  margin: 0 auto;
}

.guide-card {
  border-radius: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h2 {
  margin: 0;
  font-size: 20px;
}

.section-content {
  padding: 12px 0;
  line-height: 1.8;
}

.section-content h4 {
  margin: 16px 0 8px;
  color: #303133;
}

.section-content ol {
  padding-left: 20px;
}

.section-content li {
  margin: 8px 0;
}

/* 流程图 */
.flow-diagram {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin: 16px 0;
}

.flow-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.flow-box {
  padding: 12px 16px;
  border-radius: 8px;
  background: #f0f2f5;
  font-weight: 500;
  white-space: nowrap;
}

.flow-box.primary { background: #ecf5ff; color: #409EFF; }
.flow-box.success { background: #f0f9eb; color: #67C23A; }
.flow-box.warning { background: #fdf6ec; color: #E6A23C; }
.flow-box.info { background: #f4f4f5; color: #909399; }

.hint {
  color: #909399;
  font-size: 13px;
}

/* 快捷入口 */
.shortcuts {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
</style>
