import Axios from "@/utils/Axios.js";

const getById = (id) => {
    // 确保 id 在 URL 中以键值对的形式出现
    return Axios.get(`/api/data_viewing/getById?id=${id}`);
}

const pageList = (page, pageSize) => {
    // 确保分页参数在 URL 中正确拼接
    return Axios.get(`/api/data_viewing/pageList?page=${page}&pageSize=${pageSize}`);
}

export default { getById, pageList }
