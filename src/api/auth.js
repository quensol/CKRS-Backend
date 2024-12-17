import axios from 'axios';

const API_URL = 'http://localhost:8000/api/v1';

// 创建axios实例
const axiosInstance = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    },
    withCredentials: false
});

export const authApi = {
    // 用户注册
    register: async (userData) => {
        try {
            console.log('注册请求数据:', {
                email: userData.email,
                phone: userData.phone,
                password: userData.password,
                confirm_password: userData.confirmPassword
            });
            
            const response = await axiosInstance.post('/auth/register', {
                email: userData.email,
                phone: userData.phone,
                password: userData.password,
                confirm_password: userData.confirmPassword
            });
            return response.data;
        } catch (error) {
            console.error('注册错误:', {
                response: error.response?.data,
                status: error.response?.status,
                headers: error.response?.headers
            });
            if (error.response?.data?.detail) {
                throw error.response.data.detail;
            } else {
                throw '注册失败，请稍后重试';
            }
        }
    },

    // 用户登录
    login: async (credentials) => {
        try {
            const response = await axiosInstance.post('/auth/login', {
                email: credentials.email,
                password: credentials.password
            });
            localStorage.setItem('user', JSON.stringify(response.data));
            return response.data;
        } catch (error) {
            throw error.response?.data?.detail || '登录失败';
        }
    }
}; 