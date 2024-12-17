import React, { useState } from 'react';
import { authApi } from '../api/auth';

const Login = () => {
  const [credentials, setCredentials] = useState({
    email: '',
    password: ''
  });
  const [error, setError] = useState('');

  const handleChange = (e) => {
    setCredentials({
      ...credentials,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const user = await authApi.login(credentials);
      // 登录成功，跳转到主页
      // history.push('/dashboard');
    } catch (error) {
      setError(error);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div>
        <input
          type="email"
          name="email"
          placeholder="邮箱"
          value={credentials.email}
          onChange={handleChange}
        />
      </div>
      <div>
        <input
          type="password"
          name="password"
          placeholder="密码"
          value={credentials.password}
          onChange={handleChange}
        />
      </div>
      {error && <div className="error">{error}</div>}
      <button type="submit">登录</button>
    </form>
  );
};

export default Login; 