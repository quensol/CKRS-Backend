import React, { useState } from 'react';
import { authApi } from '../api/auth';

const Register = () => {
  const [formData, setFormData] = useState({
    email: '',
    phone: '',
    password: '',
    confirmPassword: ''
  });
  const [errors, setErrors] = useState({});

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setErrors({});
      await authApi.register(formData);
      // 注册成功，跳转到登录页
      // history.push('/login');
    } catch (error) {
      console.error('Registration error:', error);
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail;
        if (detail.field) {
          // 设置具体字段的错误
          setErrors({
            [detail.field]: detail.message
          });
        } else {
          // 设置通用错误
          setErrors({
            general: detail
          });
        }
      } else {
        setErrors({
          general: '注册失败，请稍后重试'
        });
      }
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div>
        <input
          type="email"
          name="email"
          placeholder="邮箱"
          value={formData.email}
          onChange={handleChange}
        />
        {errors.email && <div className="error">{errors.email}</div>}
      </div>
      <div>
        <input
          type="tel"
          name="phone"
          placeholder="手机号"
          value={formData.phone}
          onChange={handleChange}
        />
        {errors.phone && <div className="error">{errors.phone}</div>}
      </div>
      <div>
        <input
          type="password"
          name="password"
          placeholder="密码"
          value={formData.password}
          onChange={handleChange}
        />
        {errors.password && <div className="error">{errors.password}</div>}
      </div>
      <div>
        <input
          type="password"
          name="confirmPassword"
          placeholder="确认密码"
          value={formData.confirmPassword}
          onChange={handleChange}
        />
        {errors.confirmPassword && <div className="error">{errors.confirmPassword}</div>}
      </div>
      {errors.general && <div className="error">{errors.general}</div>}
      <button type="submit">注册</button>
    </form>
  );
};

export default Register; 