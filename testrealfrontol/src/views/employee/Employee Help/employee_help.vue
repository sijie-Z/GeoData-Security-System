<template>
  <div class="employee-help-page page-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>系统帮助</span>
        </div>
      </template>
      <div class="help-content">
        <h2>欢迎使用空间数据追踪系统</h2>
        <p>本系统用于地理空间数据（矢量与栅格）的检索、申请、审批、水印管理与下载追踪。以下为功能说明与使用指南。</p>

        <h3>1. 数据目录</h3>
        <p>在「数据目录」中可浏览与检索全部<strong>矢量数据</strong>和<strong>栅格数据</strong>。支持按数据名称、标识或关键词搜索；可按数据类型（矢量/栅格/全部）筛选。列表中展示数据编号、名称、来源、简介等；栅格数据会显示缩略图预览。</p>
        <p>点击数据卡片或「查看详情」可打开详情与地图预览：矢量数据以矢量图层形式展示；栅格数据通过<strong>瓦片服务</strong>按需加载显示。在详情中可查看元数据并提交「数据申请」。</p>

        <h3>2. 我的申请</h3>
        <p>「我的申请」展示您提交的所有数据申请及状态（待审核、一审通过/拒绝、二审通过/拒绝、已完成等）。可查看申请编号、数据名称、申请原因、审批进度与结果。审批通过后，对应数据将出现在「我的下载」中。</p>

        <h3>3. 我的下载</h3>
        <p>仅当数据申请经双级审批并完成水印嵌入后，该数据会出现在「我的下载」。您可在此查看已批准的数据列表并执行下载。下载行为会记录在系统中，便于追溯。</p>

        <h3>4. 操作历史</h3>
        <p>「操作历史」记录您在本系统中的操作（如登录、提交申请、下载等），包括时间、IP、操作类型与状态。便于您自行核对操作记录。</p>

        <h3>5. 我的通知</h3>
        <p>管理员可向指定员工或全体员工发送站内通知。您可在「我的通知」中查看标题、内容、发送时间，并可标记为已读。</p>

        <h3>6. 个人中心</h3>
        <p>在页面右上角头像菜单中进入「个人中心」，可查看与修改个人信息（如姓名、联系方式等）及密码，具体以实际页面为准。</p>

        <h3>7. 关于系统</h3>
        <p>「关于系统」提供系统简介、版本信息与主要功能概览，便于您全面了解本平台。</p>

        <el-divider />

        <p>使用中如有问题或建议，请联系系统管理员。感谢您的使用！</p>
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
