<template>
  <div>
    <el-table :data="data.list" border>
      <el-table-column prop="id" label="申请编号" width="85" />
      <el-table-column prop="data_alias" label="数据名称" width="85"/>
      <el-table-column prop="data_id" label="矢量数据编号" width="110"/>
      <el-table-column prop="applicant_user_number" label="申请人编号" width="100"/>
      <el-table-column prop="applicant_name" label="申请人姓名" width="100"/>
      <el-table-column prop="reason" label="申请理由" />

      <el-table-column label="一审状态" width="100">
        <template v-slot="scope">
          {{ getStatusText(scope.row.first_statu) }}
        </template>
      </el-table-column>

      <el-table-column label="二审状态" width="100">
        <template v-slot="scope">
          <div v-if="scope.row.first_statu===false">
            {{getStatusText('空')}}
          </div>
          <div v-else>
            {{getStatusText(scope.row.second_statu)}}
          </div>
        </template>
      </el-table-column>

      <el-table-column label="操作" width="122.5">
        <template v-slot="scope">
          <el-button size="small" type="primary" @click="update_result(scope.row)">修改审批结果</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
  <div>
    <el-pagination
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      layout="prev, pager, next, jumper, total"
      @current-change="pageChanged"
      class="view-pagination"
    />
  </div>
</template>

<script setup>
import { reactive, onMounted, ref, computed, watch } from "vue";
import { ElMessage } from "element-plus";
import axios from "axios";
import { useUserStore } from "@/stores/userStore.js";

const basic_url=import.meta.env.VITE_API_URL

const userStore = useUserStore();
const userNumber = computed(() => userStore.userNumber);

const data = reactive({
  list: []
});
const page = ref(1);
const pageSize = ref(2);
const total = ref(0);

const pageChanged = (newPage) => {
  page.value = newPage;
};

watch(page, (newValue, oldValue) => {
  if (oldValue !== newValue) {
    if (userNumber.value === 'adm1') {
      admin1_get_approved();
    } else if (userNumber.value === 'adm2') {
      admin2_get_approved();
    }
  }
});

const getStatusText = (status) => {
  if (status === true) return '通过';
  if (status === false) return '不通过';
  if (status === null) return '待审核';
  return ''; // 默认返回空字符串
};

const admin1_get_approved = async () => {
  try {
    const response = await axios.get(`${basic_url}/api/adm1_get_approved`, {
      params: { page: page.value, pageSize: pageSize.value }
    });
    console.log('admin1_get_approved response:', response.data); // 打印数据
    if (response.data == null) {
      data.list = [];
      total.value = 0;
      return;
    }
    if (!response.data.status) {
      ElMessage.error(response.data.msg);
      return;
    }
    data.list = response.data.approved_application_data;
    total.value = response.data.pages.total;
  } catch (err) {
    console.error('Error', err);
    ElMessage.error('获取记录失败');
  }
};

const admin2_get_approved = async () => {
  try {
    const response = await axios.get(`${basic_url}/api/adm2_get_approved`, {
      params: { page: page.value, pageSize: pageSize.value }
    });
    console.log('admin2_get_approved response:', response.data); // 打印数据
    if (response.data == null) {
      data.list = [];
      total.value = 0;
      return;
    }
    if (!response.data.status) {
      ElMessage.error(response.data.msg);
      return;
    }
    data.list = response.data.approved_application_data;
    total.value = response.data.pages.total;
  } catch (err) {
    console.error('Error:', err);
    ElMessage.error('获取记录失败');
  }
};


onMounted(() => {
  if (userNumber.value === 'adm1') {
    admin1_get_approved();
  } else if (userNumber.value === 'adm2') {
    admin2_get_approved();
  }
});
</script>

<style scoped>
/* 这里添加你的样式 */

.view-pagination{
  margin-top: 20px;
}

</style>
