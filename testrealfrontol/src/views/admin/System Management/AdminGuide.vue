<template>
  <div class="guide-page">
    <el-card class="guide-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <h2>管理员上手指南</h2>
          <el-tag type="success">新手必读</el-tag>
        </div>
      </template>

      <el-collapse v-model="activeSection">
        <!-- 系统概述 -->
        <el-collapse-item title="一、系统概述" name="overview">
          <div class="section-content">
            <p>本系统是<strong>空间数据跟踪系统</strong>，用于管理矢量/栅格数据的申请、审批、水印处理和分发。</p>
            <el-alert type="info" :closable="false" style="margin-top: 12px">
              <template #title>
                您当前身份：<strong>{{ adminRoleName }}</strong>，拥有以下权限
              </template>
            </el-alert>
          </div>
        </el-collapse-item>

        <!-- 管理员角色 -->
        <el-collapse-item title="二、管理员角色分工" name="roles">
          <div class="section-content">
            <el-table :data="roleData" border style="margin-top: 12px">
              <el-table-column prop="role" label="角色" width="100" />
              <el-table-column prop="permission" label="主要职责" />
              <el-table-column prop="watermark" label="水印权限" width="150" />
            </el-table>
          </div>
        </el-collapse-item>

        <!-- 审批流程 -->
        <el-collapse-item title="三、审批流程" name="approval">
          <div class="section-content">
            <div class="flow-diagram">
              <div class="flow-item">
                <div class="flow-box">员工提交申请</div>
                <el-icon><ArrowRight /></el-icon>
              </div>
              <div class="flow-item">
                <div class="flow-box primary">管理员1 一审</div>
                <el-icon><ArrowRight /></el-icon>
              </div>
              <div class="flow-item">
                <div class="flow-box success">管理员2 二审</div>
                <el-icon><ArrowRight /></el-icon>
              </div>
              <div class="flow-item">
                <div class="flow-box warning">水印处理</div>
                <el-icon><ArrowRight /></el-icon>
              </div>
              <div class="flow-item">
                <div class="flow-box info">数据分发</div>
              </div>
            </div>
            <el-divider />
            <h4>审批操作步骤：</h4>
            <ol>
              <li>进入【审批管理】-【待一审/待二审】</li>
              <li>查看申请详情，包括申请理由、数据信息</li>
              <li>点击【通过】或【拒绝】，拒绝需填写理由</li>
              <li>二审通过后，系统自动处理水印</li>
            </ol>
          </div>
        </el-collapse-item>

        <!-- 水印流程 -->
        <el-collapse-item title="四、水印处理流程" name="watermark">
          <div class="section-content">
            <el-steps :active="3" finish-status="success" simple style="margin-bottom: 20px">
              <el-step title="生成" description="管理员1" />
              <el-step title="嵌入" description="管理员2" />
              <el-step title="提取" description="管理员3" />
            </el-steps>
            <el-alert type="warning" :closable="false">
              每个水印步骤由对应管理员负责，需按顺序操作。嵌入后的数据会自动添加追踪信息。
            </el-alert>
          </div>
        </el-collapse-item>

        <!-- 数据回收 -->
        <el-collapse-item title="五、数据回收审议" name="recall">
          <div class="section-content">
            <p>当已分发的数据需要收回时（如发现违规使用），可通过回收审议流程：</p>
            <ol>
              <li>任何管理员可发起回收提议</li>
              <li>其他管理员进行投票（支持/反对/弃权）</li>
              <li>超过50%的管理员反对，数据将被收回</li>
              <li>用户会收到通知，无法继续下载</li>
            </ol>
          </div>
        </el-collapse-item>

        <!-- 在线沟通 -->
        <el-collapse-item title="六、在线沟通" name="chat">
          <div class="section-content">
            <p>管理员可与员工或其他管理员实时沟通：</p>
            <el-button type="primary" @click="goToChat">进入在线沟通</el-button>
            <el-divider direction="vertical" />
            <span class="hint">支持查看所有用户列表，直接发起对话</span>
          </div>
        </el-collapse-item>

        <!-- 常见问题 -->
        <el-collapse-item title="七、常见问题" name="faq">
          <div class="section-content">
            <el-collapse>
              <el-collapse-item title="Q: 忘记密码怎么办？" name="q1">
                <p>A: 联系系统管理员重置密码。</p>
              </el-collapse-item>
              <el-collapse-item title="Q: 如何查看操作记录？" name="q2">
                <p>A: 进入【系统设置】-【操作日志】，可查看所有操作记录。</p>
              </el-collapse-item>
              <el-collapse-item title="Q: 如何发送系统公告？" name="q3">
                <p>A: 进入【系统设置】-【系统公告】，发布公告后所有用户可见。</p>
              </el-collapse-item>
              <el-collapse-item title="Q: 审批时看不懂数据怎么办？" name="q4">
                <p>A: 可通过【在线沟通】联系申请人了解详情，或拒绝并注明疑问。</p>
              </el-collapse-item>
            </el-collapse>
          </div>
        </el-collapse-item>
      </el-collapse>
    </el-card>

    <!-- 快捷入口 -->
    <el-card class="shortcuts-card" shadow="hover" style="margin-top: 16px">
      <template #header>
        <span>快捷入口</span>
      </template>
      <div class="shortcuts">
        <el-button type="primary" @click="goTo('/admin/approve_application/not_approved')">待审批</el-button>
        <el-button type="success" @click="goTo('/admin/employee_management/information_list')">员工列表</el-button>
        <el-button type="warning" @click="goTo('/admin/system/chat')">在线沟通</el-button>
        <el-button type="info" @click="goTo('/admin/logs')">操作日志</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/userStore'
import { ArrowRight } from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()

const activeSection = ref(['overview'])

const adminRoleName = computed(() => {
  const num = (userStore.userNumber || '').toLowerCase()
  if (num.includes('admin1') || num.includes('adm1') || num === '22200214135') return '管理员1（一审）'
  if (num.includes('admin2') || num.includes('adm2') || num === '33300214135') return '管理员2（二审）'
  if (num.includes('admin3') || num.includes('adm3') || num === '44400214135') return '管理员3（提取）'
  return '管理员'
})

const roleData = [
  { role: '管理员1', permission: '一审审批、水印生成', watermark: '生成' },
  { role: '管理员2', permission: '二审审批、水印嵌入', watermark: '嵌入' },
  { role: '管理员3', permission: '水印提取、附加审议', watermark: '提取' },
]

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
